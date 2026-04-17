from minio import Minio


from src.document.config import settings

ACCESS_KEY = settings.minio_root_user
SECRET_KEY = settings.minio_root_password
ENDPOINT = settings.endpoint
BUCKET_NAME = settings.bucket_name

# 获取 MinIO 客户端
async def get_minio_client() -> Minio:
    return Minio(
        ENDPOINT,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        secure=False
    )

