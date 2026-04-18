# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text
from app.database.models.user import User
from app.database.schemas.user import UserCreate, UserUpdate, UserOut
from app.core.security import hash_password, verify_password
from fastapi import HTTPException, status
from typing import Optional, List
from datetime import datetime

from app.services.message_service import QueueService


class UserService:
    async def create_user(self, session: AsyncSession, user_in: UserCreate) -> UserOut:
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

        # 2. 发送消息：直接传 db
        # 这样，如果 publish 失败，或者后续报错，整个事务会一起回滚
        await QueueService.publish(
            db=session,
            topic="email",
            payload={"user": "user_in.user_name", "type": "welcome"}
        )

        await session.commit()  # 提交事务
        await session.refresh(user)
        return UserOut.from_orm(user)

    async def get_user(self, session: AsyncSession, user_id: int) -> Optional[UserOut]:
        user = await session.get(User, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserOut.from_orm(user)

    async def list_users(self, session: AsyncSession) -> List[UserOut]:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return [UserOut.from_orm(user) for user in users]

    async def update_user(
        self,
        session: AsyncSession,
        user_id: int,
        user_in: UserUpdate,
        current_user
    ) -> UserOut:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        if user.id != current_user['user_id']:
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
        if user_in.whats_up:
            user.whats_up = user_in.whats_up
        if user_in.avatar_id:
            user.avatar_id = user_in.avatar_id
        await session.commit()
        await session.refresh(user)
        return UserOut.from_orm(user)

    async def delete_user(self, session: AsyncSession, user_id: int, current_user: User) -> None:
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

    async def login_user(self, session: AsyncSession, identifier: str, password: str) -> UserOut:
        result = await session.execute(
            select(User).filter(or_(User.user_name == identifier, User.email == identifier))
        )
        user = result.scalars().first()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        user.last_login = datetime.utcnow()
        await session.commit()
        return UserOut.from_orm(user)

    @staticmethod
    async def login_user2(session: AsyncSession, identifier: str, password: str) -> UserOut:
        # 1. 编写原生 SQL
        # 注意：这里显式列出所有字段，确保顺序与数据库表一致
        sql = text("""
                SELECT id, user_name, email, whats_up, phone, hashed_password, 
                       is_active, created_at, updated_at, last_login
                FROM users
                WHERE user_name = :identifier OR email = :identifier
            """)

        # 2. 执行查询
        result = await session.execute(sql, {"identifier": identifier})

        # 3. 获取数据
        # result.mappings().first() 会返回一个类似字典的对象 (RowMapping)
        # 它比 scalars() 更适合原生 SQL 转 Pydantic
        row = result.mappings().first()

        # 4. 验证用户和密码
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # row['column_name'] 访问字段
        if not verify_password(password, row['hashed_password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials 密码校验不通过"
            )

        # 5. 更新 last_login
        now = datetime.utcnow()
        update_sql = text("UPDATE users SET last_login = :now WHERE id = :id")
        await session.execute(update_sql, {"now": now, "id": row['id']})
        await session.commit()

        # 6. 序列化返回
        # 方案 A：如果 row 包含 UserOut 不需要的字段（如 hashed_password），
        # Pydantic v2 默认会忽略多余字段，或者你可以手动过滤。
        # 为了性能，直接转 dict 传给 Pydantic 即可。

        # 重要：此时 row 中 last_login 是旧值，我们需要把最新的时间传给返回对象
        # 方法一：手动构建字典 (最安全)
        user_dict = dict(row)
        user_dict['last_login'] = now

        return UserOut(**user_dict)