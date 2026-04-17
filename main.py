from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.auth.models import User
from src.auth.schemas import UserCreate, UserRead, UserUpdate
from src.auth.users import fastapi_users,current_active_user
from src.auth.router import register_fastapi_users_routes

from src.document.router import document_router
from src.document.dependencies import BUCKET_NAME, get_minio_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 检查 MinIO 存储桶是否存在，如果不存在则创建
    minio_client = await get_minio_client()
    found = minio_client.bucket_exists(BUCKET_NAME)
    if not found:
        minio_client.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created.")
    else:
        print(f"Bucket '{BUCKET_NAME}' already exists.")
    yield
    # 在应用关闭时执行的代码
    print("Application is shutting down...")

app = FastAPI(lifespan=lifespan,
              title="FastAPI Users Example",
              description="FastAPI Users with JWT authentication.",
              version="1.0.0")

app.include_router(document_router,tags=["documents"])

register_fastapi_users_routes(app, fastapi_users)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}

