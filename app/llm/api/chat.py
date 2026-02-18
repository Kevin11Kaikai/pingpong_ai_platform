"""
聊天 API 模块
提供智能对话和知识库搜索接口
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.llm.schemas import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.llm.core.rag_service import get_rag_service
from app.llm.core.conversation_service import ConversationService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """
    智能对话接口

    支持 RAG 增强，自动管理对话历史

    - 如果不传 conversation_id，会创建新会话
    - 如果 use_rag=True，会检索知识库并增强回答
    - 消息会自动保存到对话历史
    """
    try:
        conv_service = ConversationService(db)
        rag_service = get_rag_service()

        # 获取或创建会话
        conversation_id = request.conversation_id
        if conversation_id:
            conversation = await conv_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
        else:
            conversation = await conv_service.create_conversation()
            conversation_id = conversation.id

        # 获取对话历史
        history = await conv_service.get_chat_history(conversation_id, limit=10)

        # 保存用户消息
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        # RAG 生成
        rag_response = await rag_service.generate_with_context(
            query=request.message,
            conversation_history=history,
            top_k=5,
            use_rag=request.use_rag,
            model=request.model,
            temperature=request.temperature,
            stream=False,
        )

        # 保存助手回复
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=rag_response.content,
            tokens_used=rag_response.tokens_used,
        )

        # 自动生成标题（如果是新会话且没有标题）
        conversation = await conv_service.get_conversation(conversation_id)
        if conversation and not conversation.title:
            # 使用用户第一条消息的前30个字符作为标题
            title = request.message[:30]
            if len(request.message) > 30:
                title += "..."
            await conv_service.update_title(conversation_id, title)

        logger.info(f"对话完成: conversation_id={conversation_id}")

        return ChatResponse(
            message=rag_response.content,
            conversation_id=conversation_id,
            sources=rag_response.sources if rag_response.sources else None,
            tokens_used=rag_response.tokens_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    流式对话接口

    使用 Server-Sent Events (SSE) 返回流式响应

    - 流式返回生成的内容
    - 最后会返回一个包含完整信息的 [DONE] 事件
    """
    try:
        conv_service = ConversationService(db)
        rag_service = get_rag_service()

        # 获取或创建会话
        conversation_id = request.conversation_id
        if conversation_id:
            conversation = await conv_service.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
        else:
            conversation = await conv_service.create_conversation()
            conversation_id = conversation.id

        # 获取对话历史
        history = await conv_service.get_chat_history(conversation_id, limit=10)

        # 保存用户消息
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )

        async def generate():
            full_response = []
            try:
                generator = await rag_service.generate_with_context(
                    query=request.message,
                    conversation_history=history,
                    top_k=5,
                    use_rag=request.use_rag,
                    model=request.model,
                    temperature=request.temperature,
                    stream=True,
                )
                async for chunk in generator:
                    full_response.append(chunk)
                    yield f"data: {chunk}\n\n"

                # 保存完整响应
                complete_response = "".join(full_response)
                await conv_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=complete_response,
                )

                # 发送完成信号
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-Id": conversation_id,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"流式对话处理失败: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
) -> SearchResponse:
    """
    知识库搜索

    仅返回检索结果，不调用 LLM 生成
    """
    try:
        rag_service = get_rag_service()
        results = rag_service.search_only(
            query=request.query,
            top_k=request.top_k,
        )

        items = [
            SearchResultItem(
                content=r.content,
                source=r.source,
                score=r.score,
                chunk_index=r.chunk_index,
            )
            for r in results
        ]

        logger.debug(f"搜索完成: query='{request.query[:30]}...', 结果数={len(items)}")

        return SearchResponse(
            results=items,
            query=request.query,
        )

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
