from fastapi import Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.database.management.base import Base
from src.utils.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    url=settings.database_url,
    echo=settings.debug
)

session_engine = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with session_engine() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]