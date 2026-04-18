from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from datetime import datetime
from fastapi import HTTPException

class LikeService:
    @staticmethod
    async def toggle_like(db: AsyncSession, tweet_id: int, user_id: int) -> dict:
        """切换点赞状态（点赞/取消点赞）"""
        # 检查是否已点赞
        check_sql = text("""
            SELECT id FROM tweet_likes 
            WHERE tweet_id = :tweet_id AND user_id = :user_id
        """)
        result = await db.execute(check_sql, {"tweet_id": tweet_id, "user_id": user_id})
        existing = result.fetchone()
        
        if existing:
            # 取消点赞
            delete_sql = text("""
                DELETE FROM tweet_likes 
                WHERE tweet_id = :tweet_id AND user_id = :user_id
            """)
            await db.execute(delete_sql, {"tweet_id": tweet_id, "user_id": user_id})
            await db.commit()
            return {"liked": False, "message": "已取消点赞"}
        else:
            # 添加点赞
            insert_sql = text("""
                INSERT INTO tweet_likes (tweet_id, user_id, created_at)
                VALUES (:tweet_id, :user_id, :now)
            """)
            await db.execute(insert_sql, {
                "tweet_id": tweet_id, 
                "user_id": user_id, 
                "now": datetime.now()
            })
            await db.commit()
            return {"liked": True, "message": "已点赞"}
    
    @staticmethod
    async def get_like_count(db: AsyncSession, tweet_id: int) -> int:
        """获取点赞数"""
        sql = text("""
            SELECT COUNT(*) FROM tweet_likes WHERE tweet_id = :tweet_id
        """)
        result = await db.execute(sql, {"tweet_id": tweet_id})
        return result.scalar() or 0
    
    @staticmethod
    async def is_liked(db: AsyncSession, tweet_id: int, user_id: int) -> bool:
        """检查用户是否已点赞"""
        sql = text("""
            SELECT id FROM tweet_likes 
            WHERE tweet_id = :tweet_id AND user_id = :user_id
        """)
        result = await db.execute(sql, {"tweet_id": tweet_id, "user_id": user_id})
        return result.fetchone() is not None
    
    @staticmethod
    async def get_tweet_likes(db: AsyncSession, tweet_id: int, user_id: int = None) -> dict:
        """获取推文点赞信息"""
        count = await LikeService.get_like_count(db, tweet_id)
        is_liked = False
        if user_id:
            is_liked = await LikeService.is_liked(db, tweet_id, user_id)
        
        return {
            "count": count,
            "is_liked": is_liked
        }
