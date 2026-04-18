# app/api/v1/endpoints/user.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from starlette.responses import JSONResponse

from app.core.check_user import get_user_or_401
from app.core.security import create_access_token
from app.database.models.user import User
from app.database.schemas.user import UserCreate, UserUpdate, UserOut
from app.database.session import get_session
from app.dependencies.auth import get_current_user
from app.middleware.custom_middleware import make_nonce
from app.services.user_service import UserService
from typing import List

router = APIRouter()
user_service = UserService()


@router.post("/login", response_model=UserOut)
async def login_user(user_login: UserCreate, session: AsyncSession = Depends(get_session)):
    # 从请求体获取数据
    identifier = user_login.user_name or user_login.email
    password = user_login.password
    user = await user_service.login_user2(session, identifier, password)

    user.last_login = datetime.utcnow()
    await session.commit()
    print(type(user))

    user_info = {
        "user_id": user.id,
        "user_name": user.user_name,
        "X-CSP-nonce": make_nonce(),
    }

    # 生成 JWT Token
    access_token_expires = timedelta(minutes=60 * 24 * 30)  # 设定过期时间
    access_token = create_access_token(data=user_info, expires_delta=access_token_expires)

    # 将 JWT 设置到 Cookie 中
    user_info["access_token"] = access_token
    response = JSONResponse(content=user_info)
    response.set_cookie(
        "access_token", access_token, httponly=True, secure=False, max_age=access_token_expires
    )

    return response


@router.post("/create", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    return await user_service.create_user(session, user_in)


@router.get("/get/{user_id}", response_model=UserOut)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    return await user_service.get_user(session, user_id)


@router.get("/list", response_model=List[UserOut])
async def list_users(session: AsyncSession = Depends(get_session)):
    return await user_service.list_users(session)


@router.put("/put/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_user_or_401)
):
    return await user_service.update_user(session, user_id, user_in, current_user)


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    await user_service.delete_user(session, user_id, current_user)
    return None


@router.get("/logout")
async def user_logout(response: Response):
    response.set_cookie(
        key="access_token",
        value="",
        expires="Thu, 01 Jan 1970 00:00:00 GMT",  # 一个确定的时间点
        # max_age=0,  # 也可以只设置 max_age=0，不需要 expires
        httponly=True,
        path='/'
    )

    return {'message': '登出成功'}
