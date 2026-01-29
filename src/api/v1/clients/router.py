from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.clients import schemas
from src.api.v1.clients.exception import (
    ClientConfigNotFoundError,
    ClientNotFoundError,
    ClientOperationError,
)
from src.api.v1.dependencies.auth import CurrentUser
from src.api.v1.dependencies.services import get_client_service
from src.database.connection import get_session
from src.services.client_service import ClientService


router = APIRouter()


@router.get("/", response_model=schemas.ClientListResponse)
async def list_clients(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    try:
        clients, total = await client_service.list_clients(session, skip=skip, limit=limit)
        return schemas.ClientListResponse(
            clients=[schemas.ClientResponse.model_validate(client) for client in clients],
            total=total
        )
    except Exception as exc:
        raise ClientOperationError(f"Failed to list clients: {str(exc)}")


@router.post("/", response_model=schemas.ClientResponse)
async def create_client(
    request: schemas.ClientCreateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
):
    try:
        client = await client_service.create_client(session, request.client_name)
        return schemas.ClientResponse.model_validate(client)
    except ValueError as exc:
        raise ClientOperationError(str(exc))
    except Exception as exc:
        raise ClientOperationError(f"Failed to create client: {str(exc)}")


@router.get("/{client_id}", response_model=schemas.ClientResponse)
async def get_client(
    client_id: UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
):
    try:
        client = await client_service.get_client(session, client_id)
        if not client:
            raise ClientNotFoundError()
        return schemas.ClientResponse.model_validate(client)
    except ClientNotFoundError:
        raise
    except Exception as exc:
        raise ClientOperationError(f"Failed to get client: {str(exc)}")


@router.patch("/{client_id}", response_model=schemas.ClientResponse)
async def update_client(
    client_id: UUID,
    request: schemas.ClientUpdateRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
):
    try:
        client = await client_service.update_client(session, client_id, request.client_name)
        if not client:
            raise ClientNotFoundError()
        return schemas.ClientResponse.model_validate(client)
    except ClientNotFoundError:
        raise
    except Exception as exc:
        raise ClientOperationError(f"Failed to update client: {str(exc)}")


@router.delete("/{client_id}")
async def delete_client(
    client_id: UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
):
    try:
        client = await client_service.delete_client(session, client_id)
        if not client:
            raise ClientNotFoundError()
        return {"message": "Client deleted successfully"}
    except ClientNotFoundError:
        raise
    except Exception as exc:
        raise ClientOperationError(f"Failed to delete client: {str(exc)}")


@router.get("/{client_id}/config", response_model=schemas.ClientConfigResponse)
async def get_client_config(
    client_id: UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    client_service: Annotated[ClientService, Depends(get_client_service)],
):
    try:
        config = await client_service.get_client_config(session, client_id)
        return schemas.ClientConfigResponse(config=config)
    except ValueError:
        raise ClientConfigNotFoundError()
    except Exception as exc:
        raise ClientOperationError(f"Failed to get client config: {str(exc)}")

