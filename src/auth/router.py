from fastapi import Depends, FastAPI
from fastapi_users import FastAPIUsers

from src.auth.models import User
from src.auth.schemas import UserCreate, UserRead, UserUpdate
from src.auth.users import auth_backend

def register_fastapi_users_routes(
    app: FastAPI,
    fastapi_users: FastAPIUsers,
) -> None:
    # 注册 FastAPI Users 的路由，包括认证、注册、密码重置、验证和用户管理
    app.include_router(
        fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
    )
    # 用户注册相关的路由
    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate),
        prefix="/auth",
        tags=["auth"],
    )
    # 密码重置的路由
    app.include_router(
        fastapi_users.get_reset_password_router(),
        prefix="/auth",
        tags=["auth"],
    )
    # 用户验证相关的路由
    app.include_router(
        fastapi_users.get_verify_router(UserRead),
        prefix="/auth",
        tags=["auth"],
    )
    # 用户管理相关的路由
    app.include_router(
        fastapi_users.get_users_router(UserRead, UserUpdate),
        prefix="/users",
        tags=["users"],
    )