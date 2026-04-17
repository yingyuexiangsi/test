import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, UniqueConstraint, BigInteger, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from src.base_model import Base 

class Document(Base):
    __tablename__ = "documents"

    # 文档 ID
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    # 文件名
    filename: Mapped[str] = mapped_column(String, nullable=False)
    # 注意：这里的 "user.id" 必须匹配User 模型的 __tablename__
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    # 存储在 MinIO 的路径 (例如: <user_id>/<filename>)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    # 文件状态（例如：uploaded, processing, processed, failed）
    status: Mapped[str] = mapped_column(String(64), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # 核心：复合唯一约束，确保同一个用户下文件名不重复
    __table_args__ = (
        UniqueConstraint("owner_id", "filename", name="uq_owner_document_filename"),
    )