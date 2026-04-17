from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # MinIO 配置
    endpoint: str
    minio_root_user: str
    minio_root_password: str
    bucket_name: str

    # Paddle OCR 配置
    paddle_ocr_api_key: str
    paddle_ocr_api_url: str

    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore",env_file_encoding="utf-8")

def get_settings():
    return Settings()


settings = get_settings()