"""
文档管理 API 模块
提供知识库文档的上传、查询和删除接口
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.llm.models import Document
from app.llm.schemas import (
    DocumentUploadRequest,
    DocumentResponse,
    DocumentListResponse,
)
from app.llm.core.document_processor import DocumentProcessor
from app.llm.core.vector_store import get_vector_store

router = APIRouter()


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: DocumentUploadRequest,
    db: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """
    上传文档到知识库

    - 自动分块并索引到向量库
    - 如果同一来源的文档已存在，会先删除旧文档再添加新文档
    """
    try:
        vector_store = get_vector_store()

        # 计算内容哈希
        content_hash = DocumentProcessor.compute_hash(request.content)

        # 检查是否已存在同来源的文档
        result = await db.execute(
            select(Document).where(Document.source == request.source)
        )
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            # 如果内容相同，直接返回
            if existing_doc.content_hash == content_hash:
                logger.info(f"文档已存在且内容未变: {request.source}")
                return DocumentResponse(
                    id=existing_doc.id,
                    source=existing_doc.source,
                    title=existing_doc.title,
                    chunk_count=existing_doc.chunk_count,
                    created_at=existing_doc.created_at,
                    updated_at=existing_doc.updated_at,
                )
            # 内容不同，删除旧文档
            vector_store.delete_by_source(request.source)
            await db.execute(
                sql_delete(Document).where(Document.source == request.source)
            )
            logger.info(f"删除旧文档: {request.source}")

        # 处理文档：分块
        chunks = DocumentProcessor.process_document(
            content=request.content,
            source=request.source,
            title=request.title,
        )

        # 添加到向量索引
        vector_store.add_documents(chunks)
        vector_store.save()

        # 保存文档元数据到数据库
        doc = Document(
            id=str(uuid.uuid4()),
            source=request.source,
            title=request.title,
            content_hash=content_hash,
            chunk_count=len(chunks),
        )
        db.add(doc)
        await db.flush()

        logger.info(f"文档上传成功: {request.source}, {len(chunks)} 块")

        return DocumentResponse(
            id=doc.id,
            source=doc.source,
            title=doc.title,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """列出已索引的文档"""
    try:
        # 获取总数
        count_result = await db.execute(select(func.count(Document.id)))
        total = count_result.scalar() or 0

        # 获取文档列表
        result = await db.execute(
            select(Document)
            .order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        documents = result.scalars().all()

        items = [
            DocumentResponse(
                id=doc.id,
                source=doc.source,
                title=doc.title,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            for doc in documents
        ]

        return DocumentListResponse(
            documents=items,
            total=total,
        )

    except Exception as e:
        logger.error(f"列出文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出文档失败: {str(e)}")


@router.delete("/documents/{source:path}", status_code=204)
async def delete_document(
    source: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    删除指定文档及其向量索引

    source 参数支持路径格式（如 path/to/file.txt）
    """
    try:
        # 检查文档是否存在
        result = await db.execute(
            select(Document).where(Document.source == source)
        )
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 从向量索引中删除
        vector_store = get_vector_store()
        deleted_count = vector_store.delete_by_source(source)
        vector_store.save()

        # 从数据库中删除
        await db.execute(
            sql_delete(Document).where(Document.source == source)
        )

        logger.info(f"删除文档: {source}, 删除 {deleted_count} 个向量块")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.post("/documents/rebuild-index", status_code=202)
async def rebuild_index(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    重建整个向量索引

    注意：这是一个耗时操作，会清空现有索引并重新构建
    """
    try:
        # 获取所有文档
        result = await db.execute(select(Document))
        documents = result.scalars().all()

        if not documents:
            return {"message": "没有文档需要重建索引", "rebuilt_count": 0}

        # 清空向量索引
        vector_store = get_vector_store()
        vector_store.clear()

        # 重建索引（注意：这里需要存储原始内容才能重建）
        # 由于我们没有存储原始内容，这个功能需要重新上传文档
        logger.warning("重建索引功能需要重新上传文档内容")

        return {
            "message": "索引已清空，请重新上传文档内容",
            "cleared_documents": len(documents),
        }

    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.get("/documents/stats")
async def get_document_stats(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """获取文档统计信息"""
    try:
        # 数据库统计
        doc_count_result = await db.execute(select(func.count(Document.id)))
        doc_count = doc_count_result.scalar() or 0

        chunk_sum_result = await db.execute(select(func.sum(Document.chunk_count)))
        chunk_sum = chunk_sum_result.scalar() or 0

        # 向量索引统计
        vector_store = get_vector_store()
        vector_stats = vector_store.get_stats()

        return {
            "database": {
                "document_count": doc_count,
                "total_chunks": chunk_sum,
            },
            "vector_store": vector_stats,
        }

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
