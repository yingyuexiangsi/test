from __future__ import annotations

from typing import Iterable

from pymilvus import (
    AnnSearchRequest,
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    Function,
    FunctionType,
    WeightedRanker,
    connections,
    utility,
)

from src.rag.config import settings

class MilvusClient:
    """
    Milvus 客户端。

    职责：管理连接、集合/索引初始化，以及写入与检索操作。
    """

    def __init__(self) -> None:
        connections.connect(uri=settings.milvus_uri, token=settings.milvus_token)
        self._collection = self._ensure_collection()

    def _ensure_collection(self) -> Collection:
        """
        确保集合与索引存在。

        - 首次创建集合并建立索引
        - 已存在集合则补充缺失的字段/索引
        """

        if not utility.has_collection(settings.milvus_collection):
            schema = CollectionSchema(
                fields=[
                    FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema("doc_id", DataType.VARCHAR, max_length=128),
                    FieldSchema("page", DataType.INT64),
                    FieldSchema("chunk_id", DataType.VARCHAR, max_length=128),
                    FieldSchema(
                        "text",
                        DataType.VARCHAR,
                        max_length=65535,
                        enable_analyzer=True,
                        analyzer_params={"type": "english"},
                    ),
                    FieldSchema("section_path", DataType.VARCHAR, max_length=1024),
                    FieldSchema("doc_title", DataType.VARCHAR, max_length=1024),
                    FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=settings.embedding_dim),
                    FieldSchema("sparse_embedding", DataType.SPARSE_FLOAT_VECTOR),
                ]
            )
            schema.add_function(
                Function(
                    name="text_bm25_func",
                    input_field_names=["text"],
                    output_field_names=["sparse_embedding"],
                    function_type=FunctionType.BM25,
                )
            )
            collection = Collection(settings.milvus_collection, schema=schema)
            collection.create_index(
                field_name="embedding",
                index_params={
                    "index_type": "HNSW",
                    "metric_type": "IP",
                    "params": {"M": 8, "efConstruction": 64},
                },
            )
            collection.create_index(
                field_name="sparse_embedding",
                index_params={
                    "index_type": "SPARSE_INVERTED_INDEX",
                    "metric_type": "BM25",
                    "params": {},
                },
            )
        else:
            collection = Collection(settings.milvus_collection)
            indexed_fields = {index.field_name for index in collection.indexes}
            if "embedding" not in indexed_fields:
                collection.create_index(
                    field_name="embedding",
                    index_params={
                        "index_type": "HNSW",
                        "metric_type": "IP",
                        "params": {"M": 8, "efConstruction": 64},
                    },
                )
            if "sparse_embedding" not in indexed_fields:
                collection.create_index(
                    field_name="sparse_embedding",
                    index_params={
                        "index_type": "SPARSE_INVERTED_INDEX",
                        "metric_type": "BM25",
                        "params": {},
                    },
                )

        collection.load()
        return collection
    
    def insert_chunks(self, rows: list[dict]) -> None:
        """
        批量写入 chunk 行。

        - rows 为空时直接返回
        - 顺序与 schema 字段保持一致
        """
        if not rows:
            return
        self._collection.insert(
            [
                [row["doc_id"] for row in rows],
                [row["page"] for row in rows],
                [row["chunk_id"] for row in rows],
                [row["text"] for row in rows],
                [row["section_path"] for row in rows],
                [row["doc_title"] for row in rows],
                [row["embedding"] for row in rows],
            ]
        )

    def delete_by_doc_id(self, doc_id: str) -> None:
        """按 doc_id 删除已入库的向量数据。"""
        self._collection.delete(expr=f"doc_id == {doc_id}")
        self._collection.flush()

