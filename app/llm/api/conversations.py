"""
会话管理 API 模块
提供会话 CRUD 操作接口
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.llm.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageResponse,
)
from app.llm.core.conversation_service import ConversationService

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """创建新对话会话"""
    try:
        service = ConversationService(db)
        conversation = await service.create_conversation(
            user_id=request.user_id,
            title=request.title,
        )

        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=0,
        )

    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> ConversationListResponse:
    """
    列出对话会话

    - 可按 user_id 过滤
    - 按更新时间倒序排列
    """
    try:
        service = ConversationService(db)
        conversations, total = await service.list_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        items = []
        for conv in conversations:
            msg_count = await service.get_message_count(conv.id)
            items.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                user_id=conv.user_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
            ))

        return ConversationListResponse(
            conversations=items,
            total=total,
        )

    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出会话失败: {str(e)}")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    """获取会话详情，包含消息历史"""
    try:
        service = ConversationService(db)
        conversation = await service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        messages = [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tokens_used=msg.tokens_used,
                created_at=msg.created_at,
            )
            for msg in conversation.messages
        ]

        return ConversationDetailResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            messages=messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """更新会话标题"""
    try:
        service = ConversationService(db)
        conversation = await service.update_title(conversation_id, request.title)

        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")

        msg_count = await service.get_message_count(conversation_id)

        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=msg_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新会话失败: {str(e)}")


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """删除会话及其所有消息"""
    try:
        service = ConversationService(db)
        deleted = await service.delete_conversation(conversation_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="会话不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")
