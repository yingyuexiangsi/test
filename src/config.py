from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn

class Settings(BaseSettings):
    db_user: str
    db_password: str
    db_name: str
    db_port: int
    db_host: str

    # 自动构建 SQLAlchemy/SQLModel 需要的 URL
    @property
    def database_url(self) -> str:
        # 异步驱动: postgresql+asyncpg://user:pass@host:port/db
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore",env_file_encoding="utf-8")

def get_settings():
    return Settings()


settings = get_settings()