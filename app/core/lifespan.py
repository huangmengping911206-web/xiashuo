# app/core/lifespan.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from app.core.logging import logger
from app.database.add_column import run_safe_migrations
from app.database.session import init_db, async_session_factory, engine
from app.core.config import settings
from pathlib import Path

from app.worker.cousumer import ConsumerWorker
from app.worker.schedule import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):

    # === 启动阶段 ===
    print("🚀 应用启动，初始化后台任务...")

    # 打印设置
    print(type(settings.dict().items()))
    for k, v in settings.dict().items():
        logger.info(f"加载配置：{k}: {v}")

    logger.info("Application started")
    # 初始化数据库表
    try:
        await init_db()
        logger.info("init_db success!")
    except Exception as e:
        logger.error(f"init_db failed: {e}")
        raise

    # 修改数据库
    await run_safe_migrations(engine)  # 增加数据库列


    # ================= 启动时执行 =================
    print("🚀 服务启动，清理僵尸任务...")
    async with async_session_factory() as db:
        # 将所有 processing 重置为 pending
        # 注意：SQLite 并发写入能力弱，这行语句执行时最好快进快出
        stmt = text("UPDATE message_queue SET status = 'pending' WHERE status = 'processing'")
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount > 0:
            print(f"♻️ 成功重置 {result.rowcount} 条僵尸任务")
    # ==========================================
    # 1. 初始化消费者任务

    # 场景：我们需要监听两个 Topic
    # "email" topic: 模拟 IO 密集型，并发设为 10
    email_worker = ConsumerWorker(topic="email", max_concurrent=2)
    # "report" topic: 模拟 CPU 密集型，并发设为 2 (避免把 CPU 打满)
    report_worker = ConsumerWorker(topic="report", max_concurrent=1)

    report_worker = ConsumerWorker(topic="chat", max_concurrent=1)

    # 将它们放入任务列表
    tasks = [
        asyncio.create_task(email_worker.loop()),
        asyncio.create_task(report_worker.loop()),
    ]
    # 3. 启动定时任务调度器
    setup_scheduler()  # 添加任务
    scheduler.start()  # 启动调度器
    print("🚀 APScheduler 已启动")


    try:
        yield
    except Exception as e:
        logger.error(f" {e}")

    # === 关闭阶段 ===
    print("👋 应用关闭，取消后台任务...")
    # 发送取消信号给所有任务
    for task in tasks:
        task.cancel()

    # 等待所有任务真正结束 (捕获 CancelledError 以避免报错)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("Application stopped")
