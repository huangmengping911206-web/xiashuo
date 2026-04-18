# app/database/models/user.py
import json

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

from app.database.models import Base


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    # 建立外键，关联到 users 表的 id (注意类型要和 User.id 一致)
    creater_id = Column(Integer, ForeignKey("users.id"), index=True)
    # 【修改1】字段名改为 content，类型改为 Text，移除 index=True
    tweet = Column(Text, nullable=False, comment="推文内容")

    # 【修改2】标签列也不需要普通索引，FTS会处理，或者以后单独建标签表
    tags = Column(Text, nullable=True, comment="标签")
    # 图片ID列表 (存储 JSON 字符串)
    image_ids = Column(Text, nullable=True, comment="图片ID列表")

    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(Boolean, default=True)
    # 修改字段名为 image_ids，明确语义
    image_ids = Column(Text, nullable=True, comment="图片ID列表(JSON字符串)")

    # 【技巧】封装属性，让代码操作更方便
    @property
    def images(self) -> list[int]:
        """自动将 JSON 字符串转为列表"""
        if self.image_ids:
            return json.loads(self.image_ids)
        return []

    @images.setter
    def images(self, value: list[int]):
        """自动将列表转为 JSON 字符串存储"""
        self.image_ids = json.dumps(value)

    # 【关键】定义 ORM 关系
    # 这里的 "User" 指向 User 模型类
    # backref="tweets" 表示在 User 模型中会自动生成一个 .tweets 属性来访问该用户的所有推文
    creater = relationship("User", backref="tweets")

    # 把SQLAlchemy查询对象转换成字典
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}