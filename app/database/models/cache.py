from sqlalchemy import Column, String, Text, DateTime, Index
from datetime import datetime
from app.database.models import Base


class CacheStore(Base):
    __tablename__ = "cache_store"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text, nullable=True)  # 存 JSON 字符串
    expire_at = Column(DateTime, nullable=True, index=True)  # 过期时间

