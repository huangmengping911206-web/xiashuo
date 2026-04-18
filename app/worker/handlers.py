import asyncio
import inspect
import logging
from time import sleep

from app.core.socket_manager import manager

logger = logging.getLogger(__name__)


# ==========================================
# 1. 定义具体的业务处理函数
# ==========================================

# 情况 A: 异步函数 (适合 IO 密集型，如发邮件、调 API)
def handle_send_email(payload: dict):
    logger.info(f"📧 [异步] 准备发送邮件: {payload}")
    # await asyncio.sleep(1)  # 模拟 IO 耗时
    sleep(5)
    print(f"📧 [异步] 准备发送邮件: {payload}")
    logger.info(f"✅ [异步] 邮件发送完毕")


# 情况 B: 同步函数 (适合 CPU 密集型，如计算、图像处理)
def handle_generate_report(payload: dict):
    # 注意：这是一个同步函数，不要加 async
    import time
    logger.info(f"📊 [同步] 开始生成报表...")
    time.sleep(2)  # 模拟 CPU 计算耗时
    logger.info(f"✅ [同步] 报表生成完毕")


# 情况 C: 默认处理函数
async def handle_default(payload: dict):
    logger.warning(f"⚠️ 未知 Topic，无法处理: {payload}")


async def handle_send_msg(payload: dict):
    '''
    发送chat消息
    :param payload: {
              "event": "send_message",
              "data": {
                    "event": "new_message",
                    "msg_data": msg_data,
                    "member_ids": member_ids
                }
            }
    :return:
    '''

    logger.info(f"📧 [异步] 准备发送chat消息: {payload}")
    data = payload.get('data', None)
    member_ids = data.get('member_ids', None)
    print('消费', data)

    if data and member_ids:
        # 3. 推送
        for uid in member_ids:
            await manager.send_personal_message(data, uid)


# ==========================================
# 2. 定义路由表 (Topic -> Function)
# ==========================================

# 将 topic 映射到具体的函数
TOPIC_HANDLER_MAP = {
    "email": handle_send_email,
    "report": handle_generate_report,
    "chat": handle_send_msg,
    # 可以继续添加...
}


# ==========================================
# 3. 智能分发器
# ==========================================

async def dispatch(topic: str, payload: dict):
    """
    根据 topic 分发消息，自动适配异步/同步函数
    """
    # 获取处理函数，没有则用默认函数
    print('topic', topic)
    handler = TOPIC_HANDLER_MAP.get(topic, handle_default)

    logger.info(f"🚀 开始分发任务 Topic=[{topic}] Handler=[{handler.__name__}]")

    # 【核心逻辑】判断函数类型
    if inspect.iscoroutinefunction(handler):
        # 如果是 async def，直接 await
        await handler(payload)
    else:
        # 如果是普通 def (同步)，扔进线程池执行，防止阻塞主循环
        await asyncio.to_thread(handler, payload)
