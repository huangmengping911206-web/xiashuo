# app/workers/queue_consumer.py
import asyncio

from app.core.memory_cache import incr_topic, get_count, decr_topic, topic_counters
from app.services.message_service import QueueService
from app.database.session import async_session_factory
from app.worker.handlers import dispatch


class ConsumerWorker:
    def __init__(self, topic: str, max_concurrent: int = 5):
        self.topic = topic
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.check_interval = 0

    async def process_message_wrapper(self, msg_id: int, payload: dict):
        async with self.semaphore:
            try:
                # 调用统一的分发器
                await dispatch(self.topic, payload)

                # 处理成功，确认消息
                async with async_session_factory() as db:
                    await QueueService.ack(db, msg_id)
                    # 注意：ack 成功后不需要减计数器
                    # 因为我们在 consume 时就已经减掉了，代表“已取出”

            except Exception as e:
                print(f"❌ 处理失败: {e}")
                async with async_session_factory() as db:
                    await QueueService.nack(db, msg_id)
                    # 失败重试：如果消息重回 pending，这里应该把计数加回去
                    incr_topic(self.topic) # 可选，取决于是否希望立即重试

    async def loop(self):
        print(f"🚀 Worker 启动: {self.topic}")
        while True:
            try:
                # 1. 【优先查内存】极快，无 IO
                if get_count(self.topic) <= 0:
                    # 内存里是 0，绝对不查数据库,Sleep 0.05秒 或 0.1秒，对 CPU 几乎无消耗
                    await asyncio.sleep(0.05)
                    self.check_interval += 0.05

                    if self.check_interval > 10:
                        async with async_session_factory() as db:
                            msg = await QueueService.consume(db, self.topic)
                            if msg:
                                # 发现了“幽灵消息”！修正计数器
                                topic_counters[self.topic] = 1000  # 重置1000，如果已经消费完了，再重置0
                                asyncio.create_task(self.process_message_wrapper(msg['id'], msg['payload']))
                    continue

                # 2. 【内存有数】才查数据库
                async with async_session_factory() as db:
                    # 这里的 consume 会把状态改为 processing
                    msg = await QueueService.consume(db, self.topic)

                if msg:
                    # 【关键】取出消息后，内存计数 -1
                    decr_topic(self.topic)

                    # 创建任务处理
                    asyncio.create_task(self.process_message_wrapper(msg['id'], msg['payload']))
                else:
                    # 极端情况：内存显示有，但数据库没查到（比如被其他进程抢了）
                    # 兜底预估幽灵消息数量，topic_counters[self.topic] = 1000
                    topic_counters[self.topic] = 0
                    pass

            except Exception as e:
                print(f"⚠️ 系统异常: {e}")
                await asyncio.sleep(5)