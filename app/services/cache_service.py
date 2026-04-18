from sqlalchemy import select, delete, text, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from app.database.models.cache import CacheStore


class CacheService:

    @staticmethod
    async def get(db: AsyncSession, key: str):
        """获取缓存 (带惰性删除)"""
        stmt = select(CacheStore).where(CacheStore.key == key)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        # 惰性删除：如果存在且已过期
        if cache and cache.expire_at and cache.expire_at < datetime.now():
            await db.execute(delete(CacheStore).where(CacheStore.key == key))
            await db.commit()
            return None

        if cache:
            try:
                return json.loads(cache.value)
            except:
                return cache.value
        return None

    @staticmethod
    async def set(db: AsyncSession, key: str, value: any, ex: int = None):
        """设置缓存"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        expire_at = datetime.now() + timedelta(seconds=ex) if ex else None

        # 使用 SQLite 的 INSERT OR REPLACE 语法 (UPSERT)
        stmt = text("""
            INSERT OR REPLACE INTO cache_store (key, value, expire_at)
            VALUES (:key, :value, :expire_at)
        """)
        await db.execute(stmt, {"key": key, "value": value_str, "expire_at": expire_at})
        await db.commit()

    @staticmethod
    async def clear_expired(db: AsyncSession):
        """定期清理过期缓存 (由后台任务调用)"""
        now = datetime.now()
        await db.execute(delete(CacheStore).where(CacheStore.expire_at < now))
        await db.commit()

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        """
        使用原生 SQL 查询缓存统计
        """
        # 1. 查询总数
        total_sql = text("SELECT COUNT(*) as count FROM cache_store")
        total_res = await db.execute(total_sql)
        total = total_res.scalar() or 0

        # 2. 查询有效数量
        # 直接利用 SQLite 的 datetime 函数，无需 Python 传入时间
        valid_sql = text("""
                SELECT COUNT(*) as count 
                FROM cache_store 
                WHERE expire_at IS NULL OR expire_at > datetime('now')
            """)
        valid_res = await db.execute(valid_sql)
        valid = valid_res.scalar() or 0

        return {
            "total": total,
            "valid": valid,
            "expired": total - valid
        }