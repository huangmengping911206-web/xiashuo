# app/api/v1/endpoints/user.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.check_user import get_user_or_401
from app.database.models.user import User
from app.database.schemas.tweet import TweetOut, TweetCreate, TweetUpdate, TweetOutWithUser, TweetOutWithUserName
from app.database.schemas.user import UserCreate, UserUpdate, UserOut
from app.database.session import get_session
from app.core.security import hash_password, create_access_token
from app.dependencies.auth import get_current_user
from typing import List, Optional
from datetime import timedelta
from fastapi.responses import JSONResponse

from app.middleware.custom_middleware import make_nonce
from app.services import tweet_service
from app.services.tweet_service import TweetService
from fastapi import APIRouter, Depends, HTTPException, Query


router = APIRouter()
tweet_service = TweetService()


@router.post("/create", response_model=TweetOut)
async def create_tweet(
    tweet_in: TweetCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_user_or_401)
):
    """
    创建推文接口
    """
    # 2. 将从认证层获取的 user.id 传递给 service
    # 这就是你问的 creater 在哪里传递：它来自后端的认证中间件/依赖，而不是前端参数
    return await tweet_service.create_tweet(session, tweet_in, creater_id=user['user_id'])


@router.get("/get/{tweet_id}", response_model=TweetOut)
async def read_tweet(tweet_id: int, db: AsyncSession = Depends(get_session)):
    db_tweet = await TweetService.get_tweet(db, tweet_id)
    return db_tweet


@router.put("/put/{tweet_id}", response_model=TweetOut)
async def update_tweet(
        tweet_id: int,
        tweet_in: TweetUpdate,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)):
    db_tweet = await TweetService.update_tweet(db, tweet_id, tweet_in, user['user_id'])
    if db_tweet is None:
        raise HTTPException(status_code=404, detail="Tweet not found or no permission")
    return db_tweet


@router.delete("/delete/{tweet_id}", response_model=TweetOut)
async def delete_tweet(tweet_id: int, db: AsyncSession = Depends(get_session),
                       user=Depends(get_user_or_401)):
    db_tweet = await TweetService.soft_del_tweet(db, tweet_id, creater_id=user['user_id'])
    if db_tweet is None:
        raise HTTPException(status_code=404, detail="Tweet not found or no permission")
    return db_tweet


@router.get("/list", response_model=List[dict])
async def read_tweets(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        creater_id: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
        order: str = "desc",
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)):
    """
    查询推文列表：
    - 支持分页
    - 支持按人员、内容、标签筛选
    - 支持排序
    - 返回结果包含 user_name
    """
    tweets = await TweetService.get_tweet_list_with_comments(
        db,
        skip=skip,
        limit=limit,
        creater_id=creater_id,
        keyword=keyword,
        tag=tag,
        order_by_time=order
    )
    
    # 批量获取点赞信息（所有推文，不只是当前用户的）
    tweet_ids = [t['id'] for t in tweets]
    if tweet_ids:
        likes = await TweetService.get_batch_likes(db, tweet_ids, user['user_id'])
        for tweet in tweets:
            tweet_id = tweet['id']
            if tweet_id in likes:
                tweet['like_count'] = likes[tweet_id]['like_count']
                tweet['is_liked'] = likes[tweet_id]['is_liked']
            else:
                tweet['like_count'] = 0
                tweet['is_liked'] = False
    
    return tweets


@router.get("/all", response_model=List[TweetOutWithUserName])
async def read_tweets_raw(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    creater_id: Optional[int] = None,  # 注意类型改为 int，匹配数据库
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    order: str = "desc",
    db: AsyncSession = Depends(get_session)
):
    tweets = await TweetService.get_tweet_list_raw(
        db,
        skip=skip,
        limit=limit,
        creater_id=creater_id,
        keyword=keyword,
        tag=tag,
        order_by_time=order
    )
    return tweets

@router.get("/search/")
async def search_tweets(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_session)
):
    """
    全文搜索推文 (类似 ES 搜索)
    """
    results = await TweetService.search_tweets(db, keyword, skip, limit)
    return {
        "keyword": keyword,
        "count": len(results),
        "results": results
    }

# app/api/endpoints/tweets.py

@router.get("/debug/fts_check")
async def debug_fts_check(db: AsyncSession = Depends(get_session)):
    # 1. 检查主表数据量
    res_main = await db.execute(text("SELECT count(*) FROM tweets"))
    main_count = res_main.scalar()

    # 2. 检查索引表数据量
    res_fts = await db.execute(text("SELECT count(*) FROM tweets_fts"))
    fts_count = res_fts.scalar()

    # 3. 如果索引为空，尝试强制重建
    message = "索引正常"
    if fts_count == 0 and main_count > 0:
        await db.execute(text("INSERT INTO tweets_fts(tweets_fts, rank) VALUES('rebuild', 0)"))
        await db.commit()
        res_fts = await db.execute(text("SELECT count(*) FROM tweets_fts"))
        fts_count = res_fts.scalar()
        message = "索引为空，已自动重建"

    # 4. 测试原始搜索 (假设关键词是 "数据")
    # 注意：这里直接传 "数据"，不加双引号，测试最基础的匹配
    test_keyword = "数据"
    query = text("""
        SELECT t.id, t.tweet
        FROM tweets t
        JOIN tweets_fts fts ON t.id = fts.rowid
        WHERE tweets_fts MATCH :keyword
    """)
    res_search = await db.execute(query, {"keyword": test_keyword})
    search_results = res_search.mappings().all()

    return {
        "main_table_count": main_count,
        "fts_table_count": fts_count,
        "status": message,
        "search_test_keyword": test_keyword,
        "search_found_count": len(search_results),
        "search_sample": search_results[:3] # 返回前3条结果看看
    }


# ========== 点赞功能 ==========

@router.post("/{tweet_id}/like", summary="点赞/取消点赞")
async def toggle_like(
    tweet_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_user_or_401)
):
    """切换点赞状态"""
    from app.services.like_service import LikeService
    
    # 检查推文是否存在
    tweet = await TweetService.get_tweet(db, tweet_id)
    if not tweet:
        raise HTTPException(status_code=404, detail="推文不存在")
    
    result = await LikeService.toggle_like(db, tweet_id, user['user_id'])
    count = await LikeService.get_like_count(db, tweet_id)
    
    return {
        **result,
        "count": count
    }

@router.get("/{tweet_id}/likes", summary="获取点赞信息")
async def get_likes(
    tweet_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_user_or_401)
):
    """获取推文点赞信息"""
    from app.services.like_service import LikeService
    
    return await LikeService.get_tweet_likes(db, tweet_id, user['user_id'])

@router.get("/user/{user_id}/likes", summary="获取用户推文总点赞数")
async def get_user_total_likes(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_user_or_401)  # 需要认证
):
    """获取用户所有推文的总点赞数"""
    from sqlalchemy import func, select
    from app.database.models.tweet import Tweet
    from app.database.models.like import TweetLike
    
    # 子查询：获取用户的所有推文 ID
    user_tweets_subq = (
        select(Tweet.id)
        .where(Tweet.creater_id == user_id)
        .subquery()
    )
    
    # 统计这些推文的总点赞数
    total_likes_query = (
        select(func.count(TweetLike.id))
        .where(TweetLike.tweet_id.in_(user_tweets_subq))
    )
    
    result = await db.execute(total_likes_query)
    total_likes = result.scalar() or 0
    
    return {"total_likes": total_likes}

@router.get("/user/{user_id}/tweets", summary="获取用户推文总数")
async def get_user_total_tweets(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(get_user_or_401)
):
    """获取用户的所有推文总数"""
    from sqlalchemy import func, select
    from app.database.models.tweet import Tweet
    
    # 统计用户的推文总数
    total_tweets_query = (
        select(func.count(Tweet.id))
        .where(Tweet.creater_id == user_id)
    )
    
    result = await db.execute(total_tweets_query)
    total_tweets = result.scalar() or 0
    
    return {"total_tweets": total_tweets}

