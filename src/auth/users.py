import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from src.auth.models import User
from src.auth.dependencies import get_user_db
from src.auth.config import settings


# JWT 密钥
SECRET = settings.private_key

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    # 用户注册后触发的事件
    async def on_after_register(self, user: User, request: Request | None = None):
        print(f"User {user.id} has registered.")

    # 用户忘记密码后触发的事件
    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    # 用户请求验证后触发的事件
    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


# 获取用户管理器实例的依赖项
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

# 后端使用 JWT 进行认证，配置 BearerTransport 和 JWTStrategy
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# 获取当前活跃用户
current_active_user = fastapi_users.current_user(active=True)

# 获取当前活跃的超级用户
current_superuser = fastapi_users.current_user(active=True, superuser=True)



