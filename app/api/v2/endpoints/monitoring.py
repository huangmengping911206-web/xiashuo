from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.cache_service import CacheService
from app.services.message_service import QueueService

router = APIRouter()


@router.get("/cache", summary="缓存监控")
async def get_cache_monitor(
        db: AsyncSession = Depends(get_session)
):
    """
    获取缓存监控数据
    - total: 总缓存数
    - valid: 有效缓存数
    - expired: 已过期缓存数
    """
    stats = await CacheService.get_stats(db)
    return {
        "code": 200,
        "data": stats
    }


@router.get("/queue", summary="队列监控")
async def get_queue_monitor(
        topic: str = Query(None, description="指定 topic，不填则查询全部"),
        db: AsyncSession = Depends(get_session)
):
    """
    获取队列监控数据
    - total: 总消息数
    - by_status: 各状态数量统计
    - by_topic: 各 topic 的状态分布 (仅当不指定 topic 时返回)
    """
    stats = await QueueService.get_stats(db, topic)
    return {
        "code": 200,
        "data": stats
    }


@router.get("/dashboard", summary="综合监控大屏")
async def get_dashboard(
        db: AsyncSession = Depends(get_session)
):
    """
    综合监控数据，一次请求获取所有关键指标
    """
    cache_stats = await CacheService.get_stats(db)
    queue_stats = await QueueService.get_stats(db)

    return {
        "code": 200,
        "data": {
            "cache": cache_stats,
            "queue": queue_stats
        }
    }
