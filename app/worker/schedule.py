from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from app.database.session import async_session_factory
from app.services.cache_service import CacheService
from app.services.message_service import QueueService

# 创建调度器实例
scheduler = AsyncIOScheduler()


async def clean_up_job():
    """
    具体的清理任务逻辑
    """
    print(f"⏰ [Scheduler] 开始执行清理任务 @ {datetime.now()}")

    # 使用 async with 自动管理会话
    async with async_session_factory() as db:
        try:
            # 1. 清理过期缓存
            deleted_cache = await CacheService.clear_expired(db)
            print(f"   -> 清理缓存: {deleted_cache} 条")

            # 2. 清理已完成队列
            deleted_queue = await QueueService.clean_done(db)
            print(f"   -> 清理队列: {deleted_queue} 条")

        except Exception as e:
            print(f"⚠️ [Scheduler] 任务执行出错: {e}")
            # 这里不需要 rollback，因为 async with 退出时如果没 commit 会自动 rollback
            # 而清理操作通常在 service 内部已经 commit 了


def setup_scheduler():
    """
    配置并启动定时任务
    """
    # 示例 1: 每隔 6 分钟执行一次 (解决了漂移问题)
    scheduler.add_job(
        clean_up_job,
        trigger=IntervalTrigger(minutes=6),
        id="clean_up_job",
        replace_existing=True
    )

    # 示例 2: 每天凌晨 3 点执行一次 (Cron 表达式，更强大)
    # scheduler.add_job(
    #     clean_up_job,
    #     trigger=CronTrigger(hour=3, minute=0),
    #     id="daily_clean_up",
    #     replace_existing=True
    # )

    print("✅ [Scheduler] 定时任务调度器配置完成")
