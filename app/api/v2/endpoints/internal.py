# app/api/v2/endpoints/internal.py
# 内部 API - 供 Claw Agent 调用，使用 API Key 认证
# 不走 Cookie/JWT，直接通过 Header 中的 API Key 鉴权

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.database.session import get_session
from app.database.schemas.tweet import TweetCreate, TweetOut
from app.services.tweet_service import TweetService
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


async def verify_internal_api_key(x_internal_key: str = Header(...)):
    """验证内部 API Key"""
    api_key = getattr(settings, 'INTERNAL_API_KEY', None)
    if not api_key:
        logger.error("INTERNAL_API_KEY 未配置")
        raise HTTPException(status_code=500, detail="服务端未配置内部 API Key")
    if x_internal_key != api_key:
        raise HTTPException(status_code=403, detail="无效的 API Key")
    return True


@router.post("/tweet/create", response_model=TweetOut, summary="内部API：创建推文")
async def internal_create_tweet(
    tweet_in: TweetCreate,
    session: AsyncSession = Depends(get_session),
    authorized: bool = Depends(verify_internal_api_key),
):
    """
    供 Claw Agent 调用的推文创建接口。
    认证方式：Header X-Internal-Key: <API_KEY>
    发推用户：由 .env 中 CLAW_USER_ID 配置
    """
    claw_user_id = getattr(settings, 'CLAW_USER_ID', None)
    if not claw_user_id:
        logger.error("CLAW_USER_ID 未配置")
        raise HTTPException(status_code=500, detail="服务端未配置 CLAW_USER_ID")

    logger.info(f"[Internal API] 创建推文, user_id={claw_user_id}, tags={tweet_in.tags}")
    tweet = await TweetService.create_tweet(session, tweet_in, creater_id=claw_user_id)
    return tweet


@router.delete("/tweet/delete/{tweet_id}", summary="内部API：删除推文")
async def internal_delete_tweet(
    tweet_id: int,
    session: AsyncSession = Depends(get_session),
    authorized: bool = Depends(verify_internal_api_key),
):
    """供 Claw Agent 调用的推文删除接口"""
    claw_user_id = getattr(settings, 'CLAW_USER_ID', None)
    if not claw_user_id:
        raise HTTPException(status_code=500, detail="服务端未配置 CLAW_USER_ID")

    # 只允许删除 CLAW 自己的推文
    from app.database.models.tweet import Tweet
    from sqlalchemy import select
    result = await session.execute(select(Tweet).where(Tweet.id == tweet_id))
    db_tweet = result.scalar_one_or_none()
    if not db_tweet:
        raise HTTPException(status_code=404, detail="推文不存在")
    if db_tweet.creater_id != claw_user_id:
        raise HTTPException(status_code=403, detail="只能删除自己的推文")

    await TweetService.delete_tweet(session, tweet_id)
    logger.info(f"[Internal API] 删除推文, tweet_id={tweet_id}")
    return {"message": "删除成功"}
