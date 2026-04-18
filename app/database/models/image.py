# app/database/models/image.py
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
# 【关键】从 base.py 导入专用的 Base
from app.database.models.base import BaseImages


# 注意：这里继承的是 BaseImages，不是原来的 Base
class Image(BaseImages):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)

    # 注意：这里去掉了 ForeignKey，因为跨库无法建立外键
    # 只存储 uploader_id，逻辑上关联
    uploader_id = Column(Integer, index=True)

    # 存储原始文件名
    filename = Column(String(255), nullable=True)

    # 【核心】存储 Base64 编码的图片数据
    image_data = Column(Text, nullable=False, comment="Base64图片数据")

    # 图片格式 (如 JPEG, PNG)
    file_type = Column(String(50), default="image/jpeg")

    # 文件大小 (Base64编码后的大小)
    file_size = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 不再定义 relationship，因为跨库 ORM 关系无法直接工作

