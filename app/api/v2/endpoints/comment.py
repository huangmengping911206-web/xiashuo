# app/api/comment.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.check_user import get_user_or_401
from app.database.schemas.comment import CommentOut, CommentCreate
from app.database.session import get_session
from app.services.comment_service import CommentService
from typing import List

router = APIRouter()


@router.post("/create", response_model=CommentOut, status_code=201)
async def create_comment(
        comment_in: CommentCreate,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401),  # 1. 在这里获取当前用户
):
    """发布评论"""
    # 实际项目中 user_id = current_user.id
    new_id = await CommentService.create_comment(db, user['user_id'], comment_in)

    # 简单返回构造的对象 (或者重新查询一次数据库获取完整信息)
    return {
        "id": new_id,
        "tweet_id": comment_in.tweet_id,
        "content": comment_in.content,
        "creater_id": user['user_id'],
        "tags": comment_in.tags,
        "created_at": datetime.utcnow()  # 简单处理
    }


@router.get("/list/{tweet_id}", response_model=List[CommentOut])
async def get_tweet_comments(
        tweet_id: int,
        skip: int = 0,
        limit: int = 20,
        db: AsyncSession = Depends(get_session)
):
    """获取某条推文下的所有评论"""
    comments = await CommentService.get_comments_by_tweet(db, tweet_id, limit, skip)
    return comments


@router.get("/get/{comment_id}", response_model=List[CommentOut])
async def get_comments(
        comment_id: int,
        db: AsyncSession = Depends(get_session)
):
    """
    获取某条推文的评论列表
    注意：这是一个公开接口，不需要 CurrentUser 依赖
    """
    comments = await CommentService.get_comment_detail(db, comment_id)
    return comments


@router.delete("/delete/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
        comment_id: int,
        user=Depends(get_user_or_401),  # 1. 在这里获取当前用户
        db: AsyncSession = Depends(get_session)
):
    """
    删除评论
    逻辑：只能删除自己的评论
    """
    # 1. 查询评论是否存在
    comment = await CommentService.get_comment_detail(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 2. 权限校验：当前用户 ID 是否等于评论的创建者 ID
    # user 对象来自依赖注入
    if comment['creater_id'] != user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除他人评论"
        )

    # 3. 执行删除
    success = await CommentService.delete_by_id(db, comment_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return None  # 204 No Content 通常返回 None