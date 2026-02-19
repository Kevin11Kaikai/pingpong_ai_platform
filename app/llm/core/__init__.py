"""
LLM 核心业务逻辑模块
"""

from app.llm.core.llm_client import LLMClient, get_llm_client
from app.llm.core.vector_store import VectorStore, get_vector_store, SearchResult
from app.llm.core.document_processor import DocumentProcessor, DocumentChunk
from app.llm.core.conversation_service import ConversationService
from app.llm.core.rag_service import RAGService, get_rag_service, RAGResponse
from app.llm.core.prompt_templates import (
    PINGPONG_SYSTEM_PROMPT,
    build_system_message,
    build_context_message,
)

__all__ = [
    # LLM 客户端
    "LLMClient",
    "get_llm_client",
    # 向量存储
    "VectorStore",
    "get_vector_store",
    "SearchResult",
    # 文档处理
    "DocumentProcessor",
    "DocumentChunk",
    # 会话服务
    "ConversationService",
    # RAG 服务
    "RAGService",
    "get_rag_service",
    "RAGResponse",
    # 提示模板
    "PINGPONG_SYSTEM_PROMPT",
    "build_system_message",
    "build_context_message",
]
