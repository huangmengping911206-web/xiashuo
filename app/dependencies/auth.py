# app/dependencies/auth.py
from fastapi import Depends, HTTPException
from app.core.logging import setup_logging

logger = setup_logging()  # 规则：始终从 app/core/logging.py 导入 setup_logging，而不是从 app.logger 导入，以避免循环导入。


async def check_cookie_or_403():
    logger.debug("检查 Cookie")
    # 你的 Cookie 验证逻辑
    raise HTTPException(status_code=403, detail="Invalid cookie")


# app/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from app.database.session import get_session
from app.core.security import verify_password
from sqlalchemy import select, or_


async def get_current_user(identifier: str, password: str, session: AsyncSession = Depends(get_session)) -> User:
    result = await session.execute(
        select(User).filter(or_(User.user_name == identifier, User.email == identifier))
    )
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials 错误的用户名或密码"
        )
    return user