import uuid
from typing import Field
from fastapi_users import schemas


# 提供基本字段和验证功能
class UserRead(schemas.BaseUser[uuid.UUID]):
    name : str| None = Field(None, max_length=64)
    pass

# 专门用于用户注册，包含强制的电子邮件和密码字段
class UserCreate(schemas.BaseUserCreate):
    pass

# 专门用于用户配置文件更新，增加了可选密码字段
class UserUpdate(schemas.BaseUserUpdate):
    name : str = Field(..., max_length=64)
    pass