from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Index
import enum
from datetime import datetime
from app.database.models import Base


class MessageStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class MessageQueue(Base):
    __tablename__ = "message_queue"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(64), index=True, nullable=False)  # 类似 Kafka Topic
    payload = Column(Text, nullable=True)  # JSON 消息体
    status = Column(String(16), default=MessageStatus.PENDING.value, index=True)
    created_at = Column(DateTime, default=datetime.now)
    processed_at = Column(DateTime, nullable=True)

    # 索引优化：根据主题和状态查询
    # 复合索引：这在单列 Column 定义中做不到，必须写在这里
    __table_args__ = (
        Index('ix_queue_topic_status', 'topic', 'status'),
    )
