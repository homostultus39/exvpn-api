from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth.exception import AuthenticationError, AuthorizationError
from src.utils.security import decode_token, verify_token_type
from src.database.connection import get_session
from src.database.models import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)]
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise AuthenticationError("Invalid token payload")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid user ID in token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_active:
        raise AuthorizationError("User is inactive")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
