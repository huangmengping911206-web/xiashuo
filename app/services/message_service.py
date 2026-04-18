from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.memory_cache import incr_topic, decr_topic


class QueueService:

    @staticmethod
    async def publish(db: AsyncSession, topic: str, payload: dict):
        """生产消息"""
        payload_str = json.dumps(payload)
        stmt = text("INSERT INTO message_queue (topic, payload, status) VALUES (:topic, :payload, 'pending')")
        await db.execute(stmt, {"topic": topic, "payload": payload_str})
        await db.commit()
        # 注意：SQLite 写是串行的，这里性能取决于磁盘 IO 和 WAL 效率
        incr_topic(topic)
        print('完成写入数据库')

    @staticmethod
    async def consume(db: AsyncSession, topic: str):
        """
        消费消息 (原子操作)
        原理：将状态从 pending 改为 processing，同时返回该行数据。
        这比 'SELECT FOR UPDATE' 更轻量，且支持高并发。
        """
        # SQLite 3.35+ 支持 RETURNING，现代 Python 环境通常支持
        stmt = text("""
            UPDATE message_queue
            SET status = 'processing', processed_at = datetime('now')
            WHERE rowid = (
                SELECT rowid FROM message_queue
                WHERE topic = :topic AND status = 'pending'
                ORDER BY id ASC
                LIMIT 1
            )
            RETURNING id, payload
        """)

        result = await db.execute(stmt, {"topic": topic})
        row = result.fetchone()  # 返回的是 Row 对象

        if row:
            await db.commit()  # 提交更新
            decr_topic(topic)
            return {"id": row[0], "payload": json.loads(row[1])}

        await db.rollback()  # 如果没查到，最好回滚一下（虽然没改动）
        return None

    @staticmethod
    async def ack(db: AsyncSession, msg_id: int):
        """确认消费 (标记为完成)"""
        await db.execute(text("UPDATE message_queue SET status = 'done' WHERE id = :id"), {"id": msg_id})
        await db.commit()

    @staticmethod
    async def nack(db: AsyncSession, msg_id: int):
        """消费失败 (重新入队)"""
        await db.execute(text("UPDATE message_queue SET status = 'pending', processed_at = NULL WHERE id = :id"),
                         {"id": msg_id})
        await db.commit()

    @staticmethod
    async def clean_done(db: AsyncSession):
        """清理已完成消息 (防止表过大)"""
        await db.execute(
            # text("DELETE FROM message_queue WHERE status = 'done' AND processed_at < datetime('now', '-1 day')"))
            text("DELETE FROM message_queue WHERE status = 'done' AND processed_at < datetime('now', '-1 day')"))
        await db.commit()
        # 建议：清理后执行 VACUUM 释放空间，但 VACUUM 会锁库，需在低峰期执行

    @staticmethod
    async def get_stats(db: AsyncSession, topic: str = None) -> dict:
        """
        使用原生 SQL 查询队列统计
        """

        # --- 1. 总数查询 ---
        if topic:
            total_sql = text("SELECT COUNT(*) FROM message_queue WHERE topic = :topic")
            total_res = await db.execute(total_sql, {"topic": topic})
        else:
            total_sql = text("SELECT COUNT(*) FROM message_queue")
            total_res = await db.execute(total_sql)

        total = total_res.scalar() or 0

        # --- 2. 按状态统计 ---
        if topic:
            status_sql = text("""
                    SELECT status, COUNT(*) as count 
                    FROM message_queue 
                    WHERE topic = :topic 
                    GROUP BY status
                """)
            status_res = await db.execute(status_sql, {"topic": topic})
        else:
            status_sql = text("""
                    SELECT status, COUNT(*) as count 
                    FROM message_queue 
                    GROUP BY status
                """)
            status_res = await db.execute(status_sql)

        by_status = {row.status: row.count for row in status_res}

        # --- 3. 按 Topic 统计 (仅当未指定 topic 时) ---
        by_topic = {}
        if not topic:
            topic_sql = text("""
                    SELECT topic, status, COUNT(*) as count 
                    FROM message_queue 
                    GROUP BY topic, status
                """)
            topic_res = await db.execute(topic_sql)

            for row in topic_res:
                if row.topic not in by_topic:
                    by_topic[row.topic] = {}
                by_topic[row.topic][row.status] = row.count

        return {
            "total": total,
            "by_status": by_status,
            "by_topic": by_topic
        }