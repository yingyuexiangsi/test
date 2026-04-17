"""
向量嵌入客户端。

职责：封装 OpenAIEmbeddings，提供批量异步嵌入接口。
"""

from __future__ import annotations

from typing import Iterable

from langchain_openai import OpenAIEmbeddings

from src.rag.config import settings


class EmbeddingClient:
    """嵌入服务客户端，负责文本批量向量化。"""

    def __init__(self) -> None:
        if not settings.embedding_base_url:
            raise ValueError("embedding_base_url is required")
        if not settings.embedding_api_key:
            raise ValueError("embedding_api_key is required")
        self._client = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )

    async def aembed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        """
        异步批量生成文本向量。

        - 空输入直接返回空列表
        - 按 batch_size 分批调用以控制请求体大小
        """
        text_list = list(texts)
        if not text_list:
            return []

        batch_size = 64
        embeddings: list[list[float]] = []
        for start in range(0, len(text_list), batch_size):
            batch = text_list[start : start + batch_size]
            embeddings.extend(await self._client.aembed_documents(batch))
        return embeddings
