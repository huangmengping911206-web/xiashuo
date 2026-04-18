# app/api/v1/endpoints/user.py
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.check_user import get_user_or_401
from app.database.models.user import User
from app.database.schemas.user import UserCreate, UserUpdate, UserOut
from app.database.session import get_session
from app.core.security import hash_password, create_access_token
from app.dependencies.auth import get_current_user
from typing import List
from datetime import timedelta
from fastapi.responses import JSONResponse

from app.middleware.custom_middleware import make_nonce

router = APIRouter()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    # 检查用户名或邮箱是否已存在
    result = await session.execute(
        select(User).filter(
            (User.user_name == user_in.user_name) | (User.email == user_in.email)
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    # 创建用户
    user = User(
        user_name=user_in.user_name,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        phone=user_in.phone
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/id/{user_id}", response_model=UserOut)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=List[UserOut])
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, 
    user_in: UserUpdate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    # 仅允许用户修改自己的信息（或管理员，需扩展）
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    if user_in.user_name:
        user.user_name = user_in.user_name
    if user_in.email:
        user.email = user_in.email
    if user_in.phone:
        user.phone = user_in.phone
    if user_in.password:
        user.hashed_password = hash_password(user_in.password)
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    await session.delete(user)
    await session.commit()
    return None


@router.post("/login", response_model=UserOut)
async def login_user(user_login: UserCreate, session: AsyncSession = Depends(get_session)):
    # 从请求体获取数据
    identifier = user_login.user_name or user_login.email
    password = user_login.password

    user = await get_current_user(identifier, password, session)
    user.last_login = datetime.utcnow()
    await session.commit()
    print(type(user))

    user_info = {
        "user_id": user.id,
        "user_name": user.user_name,
        "X-CSP-nonce": make_nonce(),
    }

    # 生成 JWT Token
    access_token_expires = timedelta(minutes=60*24*30)  # 设定过期时间
    access_token = create_access_token(data=user_info, expires_delta=access_token_expires)

    # 将 JWT 设置到 Cookie 中
    user_info["access_token"] = access_token
    response = JSONResponse(content=user_info)
    response.set_cookie(
        "access_token", access_token, httponly=True, secure=True, max_age=access_token_expires
    )

    return response
