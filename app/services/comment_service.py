# app/services/comment_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional, Dict
from app.database.schemas.comment import CommentCreate, CommentOut


class CommentService:

    @staticmethod
    async def create_comment(db: AsyncSession, user_id: int, comment_in: CommentCreate) -> int:
        """创建评论，返回新插入的 ID"""
        sql = text("""
            INSERT INTO comments (tweet_id, creater_id, content, tags, created_at, is_published)
            VALUES (:tweet_id, :creater_id, :content, :tags, datetime('now'), 1)
        """)

        result = await db.execute(sql, {
            "tweet_id": comment_in.tweet_id,
            "creater_id": user_id,
            "content": comment_in.content,
            "tags": comment_in.tags
        })
        await db.commit()
        return result.lastrowid

    @staticmethod
    async def get_comments_by_tweet(db: AsyncSession, tweet_id: int, limit: int = 20, offset: int = 0) -> List[
        CommentOut]:
        """
        获取某条推文的评论列表
        使用 LEFT JOIN 关联 users 表获取用户名
        """
        sql = text("""
            SELECT 
                c.id, c.tweet_id, c.content, c.tags, c.created_at, c.creater_id,
                u.user_name as creater_name
            FROM comments c
            LEFT JOIN users u ON c.creater_id = u.id
            WHERE c.tweet_id = :tweet_id
            ORDER BY c.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = await db.execute(sql, {
            "tweet_id": tweet_id,
            "limit": limit,
            "offset": offset
        })

        # 使用 mappings() 转为字典列表，再转 Pydantic
        rows = result.mappings().all()
        return [CommentOut(**row) for row in rows]

    @staticmethod
    async def get_list_by_tweet(
            db: AsyncSession,
            tweet_id: int,
            skip: int = 0,
            limit: int = 20
    ) -> List[CommentOut]:
        """
        查询评论列表，关联 users 表获取用户名
        """
        sql = text("""
                SELECT 
                    c.id, c.tweet_id, c.content, c.created_at, c.creater_id,
                    u.user_name as creater_name
                FROM comments c
                LEFT JOIN users u ON c.creater_id = u.id
                WHERE c.tweet_id = :tweet_id
                ORDER BY c.created_at DESC
                LIMIT :limit OFFSET :skip
            """)

        result = await db.execute(sql, {
            "tweet_id": tweet_id,
            "limit": limit,
            "skip": skip
        })

        rows = result.mappings().all()
        return [CommentOut(**row) for row in rows]

    @staticmethod
    async def get_comment_detail(db: AsyncSession, comment_id: int) -> Optional[Dict]:
        """
        查询单条评论详情（用于删除前的权限校验）
        返回字典格式，方便判断 creater_id
        """
        sql = text("SELECT id, creater_id, content FROM comments WHERE id = :id")
        result = await db.execute(sql, {"id": comment_id})
        row = result.mappings().first()
        return dict(row) if row else None

    @staticmethod
    async def delete_by_id(db: AsyncSession, comment_id: int) -> bool:
        """
        物理删除评论
        """
        sql = text("DELETE FROM comments WHERE id = :id")
        result = await db.execute(sql, {"id": comment_id})
        await db.commit()
        # rowcount 返回受影响的行数，>0 表示删除成功
        return result.rowcount > 0
