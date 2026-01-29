from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.security import hash_password
from src.database.models import User


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    username: str,
    password: str,
    is_active: bool = True
) -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        is_active=is_active
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
