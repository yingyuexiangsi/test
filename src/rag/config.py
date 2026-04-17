from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # Milvus 配置
    milvus_uri: str
    milvus_token: str
    milvus_collection: str

    # embedding 配置
    embedding_base_url: str
    embedding_api_key: str
    embedding_model: str
    embedding_dim: int 


    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore",env_file_encoding="utf-8")

def get_settings():
    return Settings()


settings = get_settings()