# app/database/schemas/user.py
import json

from pydantic import BaseModel, ConfigDict, computed_field, Field, field_validator
from typing import Optional, List
from datetime import datetime


# 基础模型：包含创建和更新共有的字段
class TweetBase(BaseModel):
    tweet: str
    tags: Optional[str] = None
    is_published: Optional[bool] = True  # 默认为 True
    # 1. 建议改为非 Optional，直接默认空列表，这样前端永远拿到的是列表
    image_ids: List[int] = []


# 创建模型：继承基础模型
class TweetCreate(TweetBase):
    # 创建时通常不需要传递 creater_id，由后端从登录用户获取
    pass


# 更新模型：所有字段都应为可选
class TweetUpdate(BaseModel):
    tweet: Optional[str] = None
    tags: Optional[str] = None
    is_published: Optional[bool] = None
    status: Optional[bool] = None
    # 注意：通常不直接更新 created_at，updated_at 由数据库自动维护



# 输出模型：返回给前端的数据结构
class TweetOut(BaseModel):
    id: int
    creater_id: int  # 注意：这里修改为 str 以匹配 SQLAlchemy 模型中的 Column(String)
    tweet: str
    tags: Optional[str] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
    status: bool
    # 1. 建议改为非 Optional，直接默认空列表，这样前端永远拿到的是列表
    image_ids: List[int] = []

    model_config = {"from_attributes": True, "extra": "ignore"}

    # 【核心解决代码】自动将 JSON 字符串转为列表
    @field_validator('image_ids', mode='before')
    @classmethod
    def parse_image_ids(cls, v):
        # 情况A：数据库是 NULL (None)
        if v is None:
            return []

        # 情况B：数据库是 JSON 字符串
        if isinstance(v, str):
            if not v:
                return []
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []

        # 情况C：已经是列表（比如手动构建时）
        return v


model_config = ConfigDict(from_attributes=True) # Pydantic v2 写法，替代 v1 的 class Config


# 简易用户 Schema (用于内部类型检查)
class UserBrief(BaseModel):
    id: int
    user_name: str
    model_config = ConfigDict(from_attributes=True)


class TweetOutWithUser(BaseModel):
    id: int
    creater_id: int
    tweet: str
    tags: Optional[str] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
    status: bool


    '''
    # 1. 定义关联字段，但标记 exclude=True
    # 这里使用 Field(exclude=True)
    # 作用：告诉 Pydantic，在生成 JSON 响应时，忽略这个字段。
    creater: Optional[UserBrief] = Field(default=None, exclude=True)  # 返回单个字段
    creater: Optional[UserBrief] = None  # 这种写法就是一个对象，包含UserBrief所有字段
    '''
    creater: Optional[UserBrief] = Field(default=None, exclude=True)


    # 2. 定义计算字段：user_name
    @computed_field
    @property
    def user_name(self) -> Optional[str]:
        """
        当访问 user_name 属性时，自动从 creater 对象中获取 user_name
        # self.creater 是上面定义的关联对象
        """
        return self.creater.user_name if self.creater else None

    model_config = ConfigDict(from_attributes=True)


# 这是一个扁平化的 Schema，直接对应 SQL 查询的列
class TweetOutWithUserName(BaseModel):
    id: int
    creater_id: int
    tweet: str
    tags: Optional[str] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
    status: bool

    # 【关键】直接定义 user_name 字段，而不是嵌套的 creater 对象
    user_name: Optional[str] = None

    # model_config = ConfigDict(from_attributes=True)

    image_ids: Optional[List[int]] = None

    model_config = {"from_attributes": True, "extra": "ignore"}

    # 【核心解决代码】自动将 JSON 字符串转为列表
    @field_validator('image_ids', mode='before')
    @classmethod
    def parse_image_ids(cls, v):
        # 情况A：数据库是 NULL (None)
        if v is None:
            return []

        # 情况B：数据库是 JSON 字符串
        if isinstance(v, str):
            if not v:
                return []
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []

        # 情况C：已经是列表（比如手动构建时）
        return v

# 带评论计数的输出模型
class TweetOutWithCommentCount(TweetOut):
    comment_count: int = 0
