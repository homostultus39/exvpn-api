from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1.auth.router import router as auth_router
from src.api.v1.clients.router import router as clients_router
from src.api.v1.server.router import router as server_router
from src.database.management.operations.user import get_user_by_username, create_user
from src.database.connection import init_database, session_engine
from src.minio.client import get_minio_client
from src.services.docker_client import close_docker_client
from src.utils.settings import get_settings


settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    minio_client = get_minio_client()
    minio_client.ensure_bucket_exists()
    await init_database()

    try:
        async with session_engine() as session:
            admin = await get_user_by_username(session, settings.admin_username)

            if not admin:
                await create_user(
                    session=session,
                    username=settings.admin_username,
                    password=settings.admin_password,
                    is_active=True
                )
                print(f"Admin user '{settings.admin_username}' created successfully")
            else:
                print(f"Admin user '{settings.admin_username}' already exists")
    except Exception as e:
        print(f"Warning: Could not initialize admin user: {e}")
        print("Please run migrations first: alembic upgrade head")

    yield

    # Shutdown
    await close_docker_client()
    print("Docker client closed")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    root_path="/api/v1",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    swagger_ui_parameters={"persistAuthorization": True}
)

app.include_router(auth_router, prefix="/auth", tags=["Authorization"])
app.include_router(server_router, prefix="/server", tags=["Server"])
app.include_router(clients_router, prefix="/clients", tags=["Clients"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "running",
        "app": settings.app_name
    }
