from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.auth.models import User
from src.auth.dependencies import get_user_db
from src.auth.schemas import UserCreate, UserRead, UserUpdate
from src.auth.users import auth_backend, current_active_user, fastapi_users, current_superuser
from src.auth.router import register_fastapi_users_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时执行的代码
    print("Application is starting up...")
    yield
    # 在应用关闭时执行的代码
    print("Application is shutting down...")

app = FastAPI(lifespan=lifespan,
              title="FastAPI Users Example",
              description="FastAPI Users with JWT authentication.",
              version="1.0.0")


register_fastapi_users_routes(app, fastapi_users)

@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_superuser)):
    return {"message": f"Hello {user.email}!"}

