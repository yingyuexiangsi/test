from fastapi import APIRouter, Depends, UploadFile, HTTPException, status
from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import timedelta
from io import BytesIO

from src.document.models import Document
from src.document.schema import UploadedResponse, DocumentCheck
from src.document.dependencies import get_minio_client, BUCKET_NAME
from src.document.ingestion import ingest_document
from src.database import get_async_session
from src.auth.users import current_superuser, current_active_user



document_router = APIRouter(prefix="/documents", tags=["documents"])


@document_router.post("/upload", response_model=UploadedResponse)
async def upload_document(file: UploadFile,
                          client = Depends(get_minio_client),
                          session: AsyncSession = Depends(get_async_session),
                          user = Depends(current_active_user)):
    """
    Upload a document to MinIO.

    Args:
        file (UploadFile): The file to be uploaded.
        client: The MinIO client instance.

    Returns:
        dict: A dictionary containing the status and message of the upload operation.
    """
    # 执行文件查重
    select_stmt = select(Document).where(Document.owner_id == user.id, Document.filename == file.filename)
    # 1. 先 await 执行语句，拿到 result 对象
    result = await session.execute(select_stmt)

    # 2. 从 result 中获取单个对象或 None
    existing_doc = result.scalar_one_or_none()

    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"名为 {file.filename} 的文件已存在于您的账户中。"
        )

    try:
        # 文件类型pdf和大小验证<50MB
        if file.content_type not in ["application/pdf"]:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                                 detail="Only PDF files are allowed.")
        file_name = file.filename
        file_content = file.file
        file_size = file.size

        storage_key = f"{user.id}/{file_name}"

        if file_size > 50 * 1024 * 1024:  # Limit file size to 50 MB
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                 detail="File size exceeds the limit of 50 MB.")
        # 上传文件到MinIO
        client.put_object(BUCKET_NAME, storage_key, file_content, file_size)

        file_uploaded_to_minio = True

        # 将文档信息保存到数据库
        new_doc = Document(
            filename=file_name,
            owner_id=user.id,
            storage_key=storage_key,
            file_size=file_size,
            status="uploaded"
        )
        session.add(new_doc)
        await session.commit()
         # 刷新以获取数据库生成的 ID
        await session.refresh(new_doc)
        return UploadedResponse(id=new_doc.id, filename=file_name, status=new_doc.status)

    except Exception as e:
        # 数据库回滚
        await session.rollback()
       # 只有当文件确实传上去了，但后续数据库操作失败时，才执行删除清理
        if file_uploaded_to_minio and storage_key:
            try:
                client.remove_object(BUCKET_NAME, storage_key)
            except Exception as cleanup_error:
                print(f"Cleanup failed: {cleanup_error}")
        print(f"Error during file upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An error occurred while MinIO uploading the file: {str(e)}")
    finally:
        await file.close()

@document_router.get("/list", response_model=List[DocumentCheck])
async def list_documents(session: AsyncSession = Depends(get_async_session),
                         user = Depends(current_active_user)):
    """
    List all documents owned by the current user.

    Args:
        session: The database session.
        user: The currently authenticated user.

    Returns:
        list: A list of documents owned by the user.
    """
    select_stmt = select(Document).where(Document.owner_id == user.id)
    result = await session.execute(select_stmt)
    documents = result.scalars().all()
    return [DocumentCheck(
        filename=doc.filename,
        file_size=doc.file_size,
        status=doc.status
    ) for doc in documents]

@document_router.get("/search", response_model=List[DocumentCheck])
async def search_documents(query: str,
                           session: AsyncSession = Depends(get_async_session),
                           user = Depends(current_active_user)):
    """
    Search for documents by filename.

    Args:
        query (str): The search query string.
        session: The database session.
        user: The currently authenticated user.

    Returns:
        list: A list of documents matching the search query.
    """
    select_stmt = select(Document).where(
        Document.owner_id == user.id,
        Document.filename.ilike(f"%{query}%")
    )
    result = await session.execute(select_stmt)
    documents = result.scalars().all()
    return [DocumentCheck(
        filename=doc.filename,
        file_size=doc.file_size,
        status=doc.status
    ) for doc in documents]


@document_router.get("/{file_name}/download")
async def get_document_url(file_name: str,
                           session: AsyncSession = Depends(get_async_session),
                           client = Depends(get_minio_client),
                           user = Depends(current_active_user)):
    """
    Generate a temporary download URL for a document.
    Args:
        file_name (str): The name of the file for which to generate the URL.
        session: The database session.
        client: The MinIO client instance.
        user: The currently authenticated user.
    
    Returns:
        dict: A dictionary containing the temporary download URL for the document.
    """
    #  从数据库查出 storage_key 和原始 filename
    select_stmt = select(Document.storage_key,Document.filename).where(
        Document.owner_id == user.id,
        Document.filename == file_name)
    
    # 先 await 执行语句，拿到 result 对象
    result = await session.execute(select_stmt)

    # mappings() 会把每行结果转成类似字典的对象
    row = result.mappings().first()

    if not row:
        raise HTTPException(status_code=404,detail="文件未找到")

    # 调用 MinIO SDK 生成一个临时链接（比如 10 分钟内有效）
    try:
        url = client.get_presigned_url(
            "GET",
            BUCKET_NAME,
            row["storage_key"],
            expires=timedelta(minutes=10), # 链接有效期
            # 关键：让浏览器下载时自动变回用户上传时的原始文件名
            response_headers={
                'response-content-disposition': f'attachment; filename="{row["filename"]}"'
            }
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail="生成链接失败")
    

@document_router.post("/{file_name}/parse", response_model=UploadedResponse)
async def parse_document(file_name: str,
                         session: AsyncSession = Depends(get_async_session),
                         client = Depends(get_minio_client),
                         user = Depends(current_active_user)):
    """
    Parse a document and store its content in the Milvus vector database.
    Args:
        file_name (str): The name of the file to be parsed.
        session: The database session
        user: The currently authenticated user.
        
    Returns:
        dict: A dictionary containing the parsing result of the document.
    """

    #  从数据库查出 document_id 和 storage_key
    stmt = select(Document).where(
        Document.owner_id == user.id,
        Document.filename == file_name
    )
    
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404,detail="文件未找到")
    
    if doc.status == "parsed":
        return UploadedResponse(id=doc.id, filename=doc.filename, status="parsed")
    
    #  从 MinIO 获取文件流
    try:
         # 更新状态为 "processing" (表示正在解析中)
        doc.status = "processing"
        await session.commit() # 先提交一次，让前端看到正在处理

        # response 是一个 urllib3.response.HTTPResponse 对象
        response = client.get_object(BUCKET_NAME, doc.storage_key)
        parse_result = await ingest_document(response, doc.id)
        
        # 解析完成后更新状态为 "parsed"
        doc.status = "parsed"
        await session.commit()
        return UploadedResponse(id=doc.id, filename=doc.filename, status=doc.status)
    except Exception as e:
        # 5. 解析失败，更新状态为 "failed"
        await session.rollback() # 回滚之前的尝试
        doc.status = "uploaded" # 恢复到上传完成但未解析的状态，允许用户重试
        await session.commit()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 无论成功失败，都要关闭连接
        response.close()
        response.release_conn()
    
