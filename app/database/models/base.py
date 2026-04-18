# app/database/base.py
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


# 这里只定义 Base，不导入任何模型
# 1. 主数据库的 Base (用于 User, Tweet)

class Base(AsyncAttrs, DeclarativeBase):
    pass


# 2. 图片数据库的 Base (用于 Image)
# 这是一个全新的 Base，它拥有独立的 metadata，不会和主数据库混淆
class BaseImages(AsyncAttrs, DeclarativeBase):
    pass
