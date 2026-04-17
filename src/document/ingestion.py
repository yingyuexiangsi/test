"""
文档解析与入库流程。

职责：负责 PDF 解析、切分、向量化与写入 Milvus。
"""

from io import BytesIO
import uuid

from src.rag.embedding_client import EmbeddingClient
from src.document.documentparse import parse_pdf_with_paddle
from src.rag.milvus_client import MilvusClient



async def ingest_document(
    fileobj,
    document_id: uuid.UUID,
):
    """
    解析并入库 PDF。

    - 调用解析服务获取结构化结果
    - 构建资产信息并写回解析结果
    - 生成向量并写入 Milvus
    """
    pdf_bytes = fileobj.read()


    # 解析 PDF
    parse_result = parse_pdf_with_paddle(BytesIO(pdf_bytes))

    # 写入向量库
    chunks = parse_result.get("chunks", [])
    texts = [chunk.get("text", "") for chunk in chunks]
    if texts:
        embeddings = await EmbeddingClient().aembed_texts(texts)
        rows = []
        for chunk, embedding in zip(chunks, embeddings, strict=False):
            rows.append(
                {
                    "doc_id": str(document_id),
                    "page": int(chunk.get("page") or 1),
                    "chunk_id": str(chunk.get("chunk_id")),
                    "text": chunk.get("text", ""),
                    "section_path": chunk.get("section_path", ""),
                    "doc_title": chunk.get("doc_title", ""),
                    "embedding": embedding,
                }
            )
        MilvusClient().insert_chunks(rows)

    return  parse_result
