# app/schemas/comment.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# 创建评论时的输入
class CommentCreate(BaseModel):
    tweet_id: int
    content: str
    tags: Optional[str] = None

# 返回给前端的输出
class CommentOut(BaseModel):
    id: int
    tweet_id: int
    content: str
    tags: Optional[str] = None
    created_at: datetime
    creater_id: int
    creater_name: Optional[str] = None  # 额外字段：通过 JOIN 查出来的用户名

    model_config = {"from_attributes": True, "extra": "ignore"}
