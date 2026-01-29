from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth.schemas import TokenResponse, LoginRequest
from src.api.v1.auth.exception import AuthenticationError
from src.database.management.operations.user import get_user_by_username
from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    verify_token_type,
)
from src.database.connection import get_session
from src.redis.client import RedisClient, get_redis_client
from src.utils.settings import get_settings

settings = get_settings()

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
):
    try:
        user = await get_user_by_username(session, request.username)

        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        await redis_client.save_access_token(
            user_id=str(user.id),
            token=access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

        await redis_client.save_refresh_token(
            user_id=str(user.id),
            token=refresh_token,
            expires_in=settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        )

        return TokenResponse(access_token=access_token)

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Login failed: {str(e)}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    refresh_token: str | None = Cookie(default=None)
):
    try:
        if not refresh_token:
            raise AuthenticationError("Refresh token not found")

        payload = decode_token(refresh_token)
        verify_token_type(payload, "refresh")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        token_in_redis = await redis_client.get_refresh_token(user_id, refresh_token)
        if not token_in_redis:
            raise AuthenticationError("Invalid or expired refresh token")

        await redis_client.delete_refresh_token(user_id, refresh_token)

        new_access_token = create_access_token(data={"sub": user_id})
        new_refresh_token = create_refresh_token(data={"sub": user_id})

        await redis_client.save_access_token(
            user_id=user_id,
            token=new_access_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )

        await redis_client.save_refresh_token(
            user_id=user_id,
            token=new_refresh_token,
            expires_in=settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60
        )

        return TokenResponse(access_token=new_access_token)

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout(
    response: Response,
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    refresh_token: str | None = Cookie(default=None)
):
    try:
        if refresh_token:
            try:
                payload = decode_token(refresh_token)
                user_id = payload.get("sub")

                if user_id:
                    await redis_client.delete_all_user_tokens(user_id)
            except Exception:
                pass

        response.delete_cookie(key="refresh_token")
        return {"message": "Successfully logged out"}

    except Exception as e:
        raise AuthenticationError(f"Logout failed: {str(e)}")