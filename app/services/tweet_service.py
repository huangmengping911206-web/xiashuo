# app/services/user_service.py
import json
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, text

from app.core.util import current_time, get_tokens, get_query_tokens
from app.database.models.tweet import Tweet
from app.database.models.user import User
from app.core.security import hash_password, verify_password
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime

from app.database.schemas.tweet import TweetCreate, TweetOut, TweetOutWithUserName


class TweetService2:
    async def create_tweet(self, session: AsyncSession, tweet_in: TweetCreate, creater) -> TweetOut:

        # 创建推文
        tweet = Tweet(
            tweet=tweet_in.tweet,
            creater_id=creater,
            tags=tweet_in.tags,
            created_at=datetime.now(),  # 获取当前时间对象,
            updated_at=datetime.now(),  # 获取当前时间对象,
            status=1,

        )
        session.add(tweet)
        await session.commit()
        await session.refresh(tweet)
        return TweetOut.from_orm(tweet)


from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, update, delete
from app.database.models.tweet import Tweet  # 假设模型文件路径
from app.database.schemas.tweet import TweetCreate, TweetUpdate
from typing import List, Optional, Tuple


class TweetService:

    @staticmethod
    async def create_tweet(session: AsyncSession, tweet_in: TweetCreate, creater_id: str) -> Tweet:
        """
        创建推文
        :param db: 数据库会话
        :param tweet_in: Pydantic 创建模型
        :param creater_id: 创建者ID (从认证层获取)
        """
        # 1. 准备数据
        # 处理 image_ids：列表 -> JSON 字符串
        # 如果数据库允许 NULL，且前端没传，则为 None
        images_json = json.dumps(tweet_in.image_ids) if tweet_in.image_ids else None

        # 创建 ORM 对象
        # 注意：tweet_in.content 对应数据库的 tweet 字段
        tweet = Tweet(
            tweet=tweet_in.tweet,
            tags=tweet_in.tags,
            image_ids=images_json,  # 存储 JSON 字符串
            creater_id=creater_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=True,
            is_published=True
        )

        session.add(tweet)
        await session.flush()  # 获取生成的 ID，但不提交事务

        # 2. 【关键】手动更新 FTS 索引表
        # 将分词后的内容存入索引表
        tokenized_content = get_tokens(tweet_in.tweet)

        await session.execute(text("""
                    INSERT INTO tweets_fts (rowid, tweet) 
                    VALUES (:id, :content)
                """), {"id": tweet.id, "content": tokenized_content})

        await session.commit()
        await session.refresh(tweet, attribute_names=["creater"])
        # return TweetOut.from_orm(tweet)
        # 3. 构建返回结果
        # 手动构建返回字典，处理别名和 JSON 反序列化
        return TweetOut.model_validate(tweet)


    @staticmethod
    async def get_tweet(db: AsyncSession, tweet_id: int) -> Optional[Tweet]:
        """获取单条推文"""
        tweet = await db.get(Tweet, tweet_id)
        if not tweet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tweet not found"
            )

        return TweetOut.model_validate(tweet)

    @staticmethod
    async def get_tweets(db: Session, skip: int = 0, limit: int = 100) -> List[Tweet]:
        """获取推文列表"""
        result = db.execute(select(Tweet).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def update_tweet(session: AsyncSession, tweet_id: int, tweet_in: TweetUpdate, creater_id: str) -> Optional[Tweet]:
        """
        更新推文
        通常需要校验 creater_id 是否有权限修改
        """
        """
            更新推文
            """
        # 1. 查询现有记录
        result = await session.execute(select(Tweet).where(Tweet.id == tweet_id))
        db_tweet = result.scalar_one_or_none()

        if not db_tweet:
            return None

        # 2. 权限校验
        if db_tweet.creater_id != creater_id:
            return None  # 或抛出 HTTPException(403)

        # 3. 获取更新数据 (排除未设置的字段)
        update_data = tweet_in.model_dump(exclude_unset=True)

        if not update_data:
            return db_tweet  # 没有数据需要更新

        # 4. 更新主表字段
        for key, value in update_data.items():
            setattr(db_tweet, key, value)

        # 5. 【关键】同步更新 FTS 索引表
        # 只有当推文内容发生改变时，才需要更新索引
        if "tweet" in update_data:
            # 对新内容进行分词
            tokenized_content = get_tokens(update_data["tweet"])

            # 更新 FTS 表
            # 注意：这里使用 UPDATE，因为 rowid 对应的记录已存在
            await session.execute(text("""
                    UPDATE tweets_fts 
                    SET tweet = :content 
                    WHERE rowid = :id
                """), {"content": tokenized_content, "id": db_tweet.id})

        # 6. 提交事务
        await session.commit()
        await session.refresh(db_tweet, attribute_names=["creater"])

        return db_tweet

    @staticmethod
    async def soft_del_tweet(db: AsyncSession, tweet_id: int, creater_id: int):
        """
        更新推文
        通常需要校验 creater_id 是否有权限修改
        """
        # 1. 查询得到 ORM 对象 (这才是数据库映射对象)
        result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
        db_obj = result.scalar_one_or_none()  # 变量名建议用 db_obj 或 db_tweet，但要清楚它是 ORM 类型

        if not db_obj:
            return None

        # 2. 直接修改 ORM 对象的属性
        # 这里的 db_obj 是 app.database.models.tweet.Tweet 类型
        db_obj.status = False
        db_obj.updated_at = datetime.now()


        try:
            # 3. 提交事务
            await db.commit()

            # 4. 刷新 ORM 对象 (从数据库获取最新状态，包括触发 onupdate 等)
            await db.refresh(db_obj)

            # 5. 最后再转换为 Pydantic 对象返回给前端
            return TweetOut.model_validate(db_obj)
        except Exception as e:
            await db.rollback()
            raise e

    @staticmethod
    async def delete_tweet(db: AsyncSession, tweet_id: int):
        """删除推文"""
        stmt = delete(Tweet).where(Tweet.id == tweet_id)
        result = db.execute(stmt)
        # 2. 删除索引表
        await db.execute(text("DELETE FROM tweets_fts WHERE rowid = :id"), {"id": tweet_id})

        await db.commit()
        return result


    @staticmethod
    async def get_tweet_list(
            db: AsyncSession,
            skip: int = 0,
            limit: int = 10,
            creater_id: Optional[str] = None,
            keyword: Optional[str] = None,
            tag: Optional[str] = None,
            order_by_time: str = "desc"
    ) -> List[TweetOut]:
        """
        复杂查询实现：
        1. 分页
        2. 过滤 is_published=0 和 status=0
        3. 支持按人员、内容、标签筛选
        4. 支持时间排序
        5. 关联查询 User
        """

        # 1. 构建基础查询
        # selectinload 用于预加载关联的 User 数据，避免 N+1 查询问题
        query = select(Tweet).options(selectinload(Tweet.creater))

        # 2. 固定过滤条件：is_published=0 和 status=0
        # 注意：在代码中建议使用 False/True，映射到数据库的 0/1
        filters = [
            Tweet.is_published == True,
            Tweet.status == True
        ]

        # 3. 动态过滤条件
        if creater_id:
            filters.append(Tweet.creater_id == creater_id)

        if keyword:
            # 模糊搜索内容
            filters.append(Tweet.tweet.like(f"%{keyword}%"))

        if tag:
            # 模糊搜索标签 (假设标签是文本字段)
            filters.append(Tweet.tags.like(f"%{tag}%"))

        # 组合所有过滤条件
        query = query.where(and_(*filters))

        # 4. 排序逻辑
        if order_by_time == "asc":
            query = query.order_by(Tweet.created_at.asc())
        else:
            query = query.order_by(Tweet.created_at.desc())

        # 5. 分页逻辑
        query = query.offset(skip).limit(limit)

        # 6. 执行异步查询
        result = await db.execute(query)
        # data = [TweetOut.model_validate(t) for t in tweets]
        #
        # return data
        tweets = result.scalars().all()

        # 3. 转换
        # 现在 t 是真正的 Tweet 模型对象，Pydantic 能正确触发验证器

        data = [TweetOut.model_validate(t) for t in tweets]
        print(data)
        # print(data[0].model_dump())  # 打印字典结构，看看有没有 image_ids

        return data


    @staticmethod
    async def get_tweet_list_raw(
            db: AsyncSession,
            skip: int = 0,
            limit: int = 10,
            creater_id: Optional[int] = None,
            keyword: Optional[str] = None,
            tag: Optional[str] = None,
            order_by_time: str = "desc"
    ) -> List[TweetOutWithUserName]:
        """
        使用原生 SQL 实现复杂查询
        """

        # 1. 构建 SELECT 部分，直接选取 user_name
        # 注意：使用 t. 和 u. 别名区分同名字段
        sql_select = """
                SELECT 
                    t.id, 
                    t.creater_id, 
                    t.tweet, 
                    t.tags, 
                    t.is_published, 
                    t.image_ids,
                    t.created_at, 
                    t.updated_at, 
                    t.status,
                    u.user_name
                FROM tweets t
                LEFT JOIN users u ON t.creater_id = u.id
            """

        # 2. 构建 WHERE 条件
        # 需求：查询过滤 is_published=0 和 status=0
        # 在 SQL 中，0 对应 False，1 对应 True
        conditions = ["t.is_published = 1", "t.status = 1"]
        params = {}  # 用于存储参数绑定，防止 SQL 注入

        # 动态条件
        if creater_id:
            conditions.append("t.creater_id = :creater_id")
            params["creater_id"] = creater_id

        if keyword:
            conditions.append("t.tweet LIKE :keyword")
            params["keyword"] = f"%{keyword}%"

        if tag:
            conditions.append("t.tags LIKE :tag")
            params["tag"] = f"%{tag}%"

        # 拼接 WHERE 子句
        sql_where = " WHERE " + " AND ".join(conditions)

        # 3. 构建排序
        # 注意：手写 SQL 时要防止注入，order_by_time 不能直接拼接字符串，
        # 必须在校验列表内，或者硬编码判断。
        if order_by_time == "asc":
            order_sql = " ORDER BY t.created_at ASC "
        else:
            order_sql = " ORDER BY t.created_at DESC "

        # 4. 构建分页
        # 参数绑定 :limit 和 :offset
        sql_pagination = " LIMIT :limit OFFSET :skip "
        params["limit"] = limit
        params["skip"] = skip

        # 5. 组合完整 SQL
        full_sql_str = sql_select + sql_where + order_sql + sql_pagination

        # 6. 执行查询
        # 使用 text() 包装 SQL 字符串
        query = text(full_sql_str)

        # 传入参数字典
        result = await db.execute(query, params)
        print(result)

        # 7. 转换结果
        # result.mappings().all() 返回的是 Row 对象列表， behave like dict
        # Pydantic 的 model_validate 可以直接解析字典
        data = [TweetOutWithUserName.model_validate(row) for row in result.mappings().all()]

        return data




    @staticmethod
    async def search_tweets(db: AsyncSession, keyword: str, skip: int = 0, limit: int = 10):
        """
        全文检索推文
        """
        if not keyword:
            return []

        # 1. 处理搜索词 (分词 + 加 * 号)
        search_query = get_query_tokens(keyword)

        # 2. 执行搜索
        # 注意：这里我们从主表 t 拿数据，因为 t.tweet 是原文，没有空格
        # 索引表 fts 只负责过滤 ID
        query = text("""
                SELECT t.id, t.tweet, t.created_at
                FROM tweets t
                JOIN tweets_fts fts ON t.id = fts.rowid
                WHERE tweets_fts MATCH :keyword
                ORDER BY t.created_at DESC
                LIMIT :limit OFFSET :offset
            """)

        result = await db.execute(query, {"keyword": search_query, "limit": limit, "offset": skip})
        return result.mappings().all()
    @staticmethod
    async def get_tweet_list_with_comments(
            db: AsyncSession,
            skip: int = 0,
            limit: int = 10,
            creater_id: Optional[str] = None,
            keyword: Optional[str] = None,
            tag: Optional[str] = None,
            order_by_time: str = "desc"
    ) -> List[dict]:
        """
        查询推文列表并附带评论计数
        """
        from sqlalchemy import func
        from app.database.models.comment import Comment
        
        comment_count_subq = (
            select(Comment.tweet_id, func.count(Comment.id).label('comment_count'))
            .where(Comment.is_published == True)
            .group_by(Comment.tweet_id)
            .subquery()
        )
        
        query = (
            select(Tweet, comment_count_subq.c.comment_count)
            .options(selectinload(Tweet.creater))
            .outerjoin(comment_count_subq, Tweet.id == comment_count_subq.c.tweet_id)
        )
        
        filters = [Tweet.is_published == True, Tweet.status == True]
        if creater_id:
            filters.append(Tweet.creater_id == creater_id)
        if keyword:
            filters.append(Tweet.tweet.like(f"%{keyword}%"))
        if tag:
            filters.append(Tweet.tags.like(f"%{tag}%"))
        
        query = query.where(and_(*filters))
        
        if order_by_time == "asc":
            query = query.order_by(Tweet.created_at.asc())
        else:
            query = query.order_by(Tweet.created_at.desc())
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        
        rows = result.all()
        data = []
        for tweet, count in rows:
            tweet_dict = TweetOut.model_validate(tweet).model_dump()
            tweet_dict['comment_count'] = count or 0
            tweet_dict['like_count'] = 0  # 默认点赞数
            tweet_dict['is_liked'] = False  # 默认未点赞
            data.append(tweet_dict)
        
        return data


    @staticmethod
    async def get_batch_likes(db: AsyncSession, tweet_ids: list, user_id: int = None) -> dict:
        """批量获取推文点赞信息"""
        from sqlalchemy import func
        from app.database.models.like import TweetLike
        
        # 获取每条推文的点赞数
        like_count_subq = (
            select(TweetLike.tweet_id, func.count(TweetLike.id).label('like_count'))
            .where(TweetLike.tweet_id.in_(tweet_ids))
            .group_by(TweetLike.tweet_id)
            .subquery()
        )
        
        query = select(like_count_subq.c.tweet_id, like_count_subq.c.like_count)
        result = await db.execute(query)
        like_counts = {row.tweet_id: row.like_count for row in result.fetchall()}
        
        # 获取当前用户的点赞状态
        user_likes = {}
        if user_id:
            user_like_query = select(TweetLike.tweet_id).where(
                TweetLike.tweet_id.in_(tweet_ids),
                TweetLike.user_id == user_id
            )
            user_like_result = await db.execute(user_like_query)
            user_likes = {row.tweet_id: True for row in user_like_result.fetchall()}
        
        # 组装结果
        result = {}
        for tweet_id in tweet_ids:
            result[tweet_id] = {
                'like_count': like_counts.get(tweet_id, 0),
                'is_liked': user_likes.get(tweet_id, False)
            }
        
        return result
