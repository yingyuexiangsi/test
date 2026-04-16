from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # postgresql参数配置
    db_user: str
    db_password: str
    db_name: str
    db_port: int
    db_host: str

    # JWT配置
    private_key: str

    # 自动构建 SQLAlchemy/SQLModel 需要的 URL
    @property
    def database_url(self) -> str:
        # 异步驱动: postgresql+asyncpg://user:pass@host:port/db
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore",env_file_encoding="utf-8")

def get_settings():
    return Settings()


settings = get_settings()