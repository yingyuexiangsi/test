from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from fastapi_users.authentication import JWTStrategy

from src.auth.models import Base, User
from src.auth.service import get_async_session
from src.config import settings


# 获取用户表
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


