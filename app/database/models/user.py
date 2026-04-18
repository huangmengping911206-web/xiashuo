# app/database/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

from app.database.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    whats_up = Column(String(255))  # 签名
    phone = Column(String(20))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    avatar_id = Column(Integer, nullable=True, comment="头像图片ID，关联图片库")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    # 【新增】扩展字段 -> JSON 列 (SQLite下用Text存)
    # 存储类似 {"theme": "dark", "notify_email": true} 的数据
    settings = Column(Text, nullable=True, comment="用户配置JSON")