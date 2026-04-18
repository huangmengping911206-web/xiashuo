# app/database/schemas/user.py
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    user_name: constr(max_length=50)
    email: EmailStr = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str  # 明文密码，稍后哈希


class UserUpdate(UserBase):
    password: Optional[str] = None
    is_active: Optional[bool] = None
    whats_up: Optional[str] = None
    avatar_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    user_name: str
    email: EmailStr
    phone: Optional[str]
    is_active: bool
    avatar_id:  Optional[int] = None
    whats_up: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True  # 支持 ORM 对象转换
