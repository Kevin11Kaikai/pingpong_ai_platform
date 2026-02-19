"""
RAG 服务模块
协调检索和生成流程
"""

from typing import List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from loguru import logger

from app.llm.schemas import ChatMessage
from app.llm.core.llm_client import LLMClient, get_llm_client
from app.llm.core.vector_store import VectorStore, SearchResult, get_vector_store
from app.llm.core.prompt_templates import (
    build_system_message,
    build_context_message,
    extract_sources,
)


@dataclass
class RAGResponse:
    """RAG 响应数据类"""
    content: str
    sources: List[str]
    tokens_used: Optional[int] = None


class RAGService:
    """
    RAG 服务
    协调检索和生成流程
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        初始化 RAG 服务

        Args:
            vector_store: 向量存储实例
            llm_client: LLM 客户端实例
        """
        self.vector_store = vector_store or get_vector_store()
        self.llm_client = llm_client or get_llm_client()

    async def generate_with_context(
        self,
        query: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        top_k: int = 5,
        use_rag: bool = True,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Union[RAGResponse, AsyncGenerator[str, None]]:
        """
        带上下文的生成

        流程:
        1. 检索相关文档
        2. 构建增强提示
        3. 调用 LLM 生成

        Args:
            query: 用户查询
            conversation_history: 对话历史
            top_k: 检索数量
            use_rag: 是否使用 RAG 检索
            model: 模型名称
            temperature: 生成温度
            stream: 是否流式

        Returns:
            RAG 响应或流式生成器
        """
        # 检索相关文档
        context_docs = []
        if use_rag:
            context_docs = self.vector_store.search(query, top_k=top_k)
            logger.debug(f"RAG 检索到 {len(context_docs)} 条相关文档")

        # 构建消息列表
        messages = self._build_messages(query, context_docs, conversation_history)

        if stream:
            # 流式模式：返回生成器，无法获取 token 使用量
            return self._stream_generate(messages, context_docs, model, temperature)
        else:
            # 非流式模式
            return await self._generate(messages, context_docs, model, temperature)

    async def _generate(
        self,
        messages: List[ChatMessage],
        context_docs: List[SearchResult],
        model: str,
        temperature: float,
    ) -> RAGResponse:
        """非流式生成"""
        content, tokens_used = await self.llm_client.chat_completion_with_tokens(
            messages=messages,
            model=model,
            temperature=temperature,
        )
        sources = extract_sources(context_docs)
        return RAGResponse(
            content=content,
            sources=sources,
            tokens_used=tokens_used,
        )

    async def _stream_generate(
        self,
        messages: List[ChatMessage],
        context_docs: List[SearchResult],
        model: str,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """流式生成"""
        generator = await self.llm_client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=True,
        )
        async for chunk in generator:
            yield chunk

    def _build_messages(
        self,
        query: str,
        context_docs: List[SearchResult],
        history: Optional[List[ChatMessage]] = None,
    ) -> List[ChatMessage]:
        """
        构建完整的消息列表

        Args:
            query: 用户查询
            context_docs: 检索到的文档
            history: 对话历史

        Returns:
            消息列表
        """
        messages = []

        # 系统消息
        system_prompt = build_system_message(use_rag=bool(context_docs))
        messages.append(ChatMessage(role="system", content=system_prompt))

        # RAG 上下文（如果有）
        context_msg = build_context_message(context_docs)
        if context_msg:
            messages.append(ChatMessage(role="system", content=context_msg))

        # 对话历史
        if history:
            # 只保留最近的消息，避免超过上下文窗口
            recent_history = history[-10:]  # 最近 10 条
            messages.extend(recent_history)

        # 当前用户消息
        messages.append(ChatMessage(role="user", content=query))

        return messages

    def search_only(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """
        仅检索，不生成

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            搜索结果列表
        """
        return self.vector_store.search(query, top_k=top_k)


# 工厂函数
def get_rag_service() -> RAGService:
    """获取 RAG 服务实例"""
    return RAGService()
