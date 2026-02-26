"""
LLM 模块测试 (Phase 2)
测试 LLM 客户端、RAG 服务、向量存储、API 端点等
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path


# ========== Schema 测试 ==========

class TestLLMSchemas:
    """LLM Schema 验证测试"""

    def test_chat_message_schema(self):
        """测试 ChatMessage Schema"""
        from app.llm.schemas import ChatMessage
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_message_roles(self):
        """测试 ChatMessage 角色限制"""
        from app.llm.schemas import ChatMessage
        from pydantic import ValidationError

        # 有效角色
        for role in ["user", "assistant", "system"]:
            msg = ChatMessage(role=role, content="test")
            assert msg.role == role

        # 无效角色
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="test")

    def test_chat_request_schema(self):
        """测试 ChatRequest Schema"""
        from app.llm.schemas import ChatRequest
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.use_rag is True  # 默认值
        assert req.model == "gpt-4o-mini"  # 默认值
        assert req.temperature == 0.7  # 默认值

    def test_chat_request_validation(self):
        """测试 ChatRequest 验证"""
        from app.llm.schemas import ChatRequest
        from pydantic import ValidationError

        # 消息不能为空
        with pytest.raises(ValidationError):
            ChatRequest(message="")

        # temperature 范围验证
        with pytest.raises(ValidationError):
            ChatRequest(message="test", temperature=3.0)

    def test_chat_response_schema(self):
        """测试 ChatResponse Schema"""
        from app.llm.schemas import ChatResponse
        resp = ChatResponse(
            message="Hello",
            conversation_id="conv-123",
            sources=["doc1.md"],
            tokens_used=100
        )
        assert resp.message == "Hello"
        assert resp.conversation_id == "conv-123"
        assert resp.sources == ["doc1.md"]

    def test_search_request_schema(self):
        """测试 SearchRequest Schema"""
        from app.llm.schemas import SearchRequest
        req = SearchRequest(query="乒乓球技术", top_k=10)
        assert req.query == "乒乓球技术"
        assert req.top_k == 10

    def test_search_response_schema(self):
        """测试 SearchResponse Schema"""
        from app.llm.schemas import SearchResponse, SearchResultItem
        item = SearchResultItem(
            content="测试内容",
            source="test.md",
            score=0.95,
            chunk_index=0
        )
        resp = SearchResponse(results=[item], query="test")
        assert len(resp.results) == 1
        assert resp.results[0].score == 0.95


# ========== LLM 客户端测试 ==========

class TestLLMClient:
    """LLM 客户端测试"""

    def test_llm_client_import(self):
        """测试 LLM 客户端导入"""
        from app.llm.core.llm_client import LLMClient
        assert LLMClient is not None

    def test_llm_client_initialization(self):
        """测试 LLM 客户端初始化"""
        from app.llm.core.llm_client import LLMClient
        client = LLMClient(
            api_key="test-key",
            base_url="https://api.example.com/v1"
        )
        assert client.base_url == "https://api.example.com/v1"
        assert client.client is not None

    @pytest.mark.asyncio
    async def test_chat_completion_format(self):
        """测试聊天补全消息格式化"""
        from app.llm.core.llm_client import LLMClient
        from app.llm.schemas import ChatMessage

        client = LLMClient(api_key="test", base_url="https://api.example.com/v1")

        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
        ]

        # Mock API 调用
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await client.chat_completion(messages, stream=False)
            assert result == "Test response"


# ========== 向量存储测试 ==========

class TestVectorStore:
    """向量存储测试"""

    def test_vector_store_import(self):
        """测试向量存储导入"""
        from app.llm.core.vector_store import VectorStore, SearchResult, ChunkMetadata
        assert VectorStore is not None
        assert SearchResult is not None
        assert ChunkMetadata is not None

    def test_vector_store_embedding_dim(self):
        """测试 Embedding 维度常量"""
        from app.llm.core.vector_store import VectorStore
        assert VectorStore.EMBEDDING_DIM == 384

    def test_vector_store_initialization(self):
        """测试向量存储初始化"""
        from app.llm.core.vector_store import VectorStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(index_dir=Path(tmpdir))
            assert store.index_dir == Path(tmpdir)
            assert store.index is None  # 未加载
            assert store.metadata == []

    def test_vector_store_create_empty_index(self):
        """测试创建空索引"""
        from app.llm.core.vector_store import VectorStore
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(index_dir=Path(tmpdir))
            store.load()
            assert store.index is not None
            assert store.index.ntotal == 0

    def test_vector_store_add_and_search(self):
        """测试添加文档和搜索"""
        from app.llm.core.vector_store import VectorStore
        from app.llm.core.document_processor import DocumentChunk

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(index_dir=Path(tmpdir))
            store.load()

            # 添加文档
            chunks = [
                DocumentChunk(
                    content="乒乓球正手攻球技术要点",
                    source="technique.md",
                    chunk_index=0,
                    title="正手技术"
                ),
                DocumentChunk(
                    content="乒乓球反手推挡技术分析",
                    source="technique.md",
                    chunk_index=1,
                    title="反手技术"
                ),
            ]
            added = store.add_documents(chunks)
            assert added == 2
            assert store.index.ntotal == 2

            # 搜索
            results = store.search("正手攻球", top_k=2)
            assert len(results) > 0
            assert results[0].source == "technique.md"

    def test_vector_store_save_and_load(self):
        """测试索引保存和加载"""
        from app.llm.core.vector_store import VectorStore
        from app.llm.core.document_processor import DocumentChunk

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并保存
            store = VectorStore(index_dir=Path(tmpdir))
            store.load()
            chunks = [
                DocumentChunk(
                    content="测试内容",
                    source="test.md",
                    chunk_index=0
                )
            ]
            store.add_documents(chunks)
            store.save()

            # 重新加载
            store2 = VectorStore(index_dir=Path(tmpdir))
            store2.load()
            assert store2.index.ntotal == 1
            assert len(store2.metadata) == 1

    def test_vector_store_get_stats(self):
        """测试获取统计信息"""
        from app.llm.core.vector_store import VectorStore
        from app.llm.core.document_processor import DocumentChunk

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(index_dir=Path(tmpdir))
            store.load()

            chunks = [
                DocumentChunk(content="内容1", source="doc1.md", chunk_index=0),
                DocumentChunk(content="内容2", source="doc1.md", chunk_index=1),
                DocumentChunk(content="内容3", source="doc2.md", chunk_index=0),
            ]
            store.add_documents(chunks)

            stats = store.get_stats()
            assert stats["total_chunks"] == 3
            assert stats["unique_sources"] == 2
            assert stats["sources"]["doc1.md"] == 2
            assert stats["sources"]["doc2.md"] == 1

    def test_vector_store_clear(self):
        """测试清空索引"""
        from app.llm.core.vector_store import VectorStore
        from app.llm.core.document_processor import DocumentChunk

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStore(index_dir=Path(tmpdir))
            store.load()

            chunks = [
                DocumentChunk(content="测试", source="test.md", chunk_index=0)
            ]
            store.add_documents(chunks)
            assert store.index.ntotal == 1

            store.clear()
            assert store.index.ntotal == 0
            assert len(store.metadata) == 0


# ========== RAG 服务测试 ==========

class TestRAGService:
    """RAG 服务测试"""

    def test_rag_service_import(self):
        """测试 RAG 服务导入"""
        from app.llm.core.rag_service import RAGService, RAGResponse
        assert RAGService is not None
        assert RAGResponse is not None

    def test_rag_response_dataclass(self):
        """测试 RAGResponse 数据类"""
        from app.llm.core.rag_service import RAGResponse
        resp = RAGResponse(
            content="回答内容",
            sources=["doc1.md", "doc2.md"],
            tokens_used=100
        )
        assert resp.content == "回答内容"
        assert len(resp.sources) == 2
        assert resp.tokens_used == 100

    def test_rag_service_build_messages(self):
        """测试消息构建"""
        from app.llm.core.rag_service import RAGService
        from app.llm.core.vector_store import SearchResult, VectorStore
        from app.llm.schemas import ChatMessage

        # 使用临时目录创建 VectorStore
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStore(index_dir=Path(tmpdir))
            vector_store.load()

            # Mock LLM client
            mock_client = MagicMock()
            service = RAGService(
                vector_store=vector_store,
                llm_client=mock_client
            )

            # 测试消息构建
            context_docs = [
                SearchResult(
                    content="相关内容",
                    source="doc.md",
                    chunk_index=0,
                    score=0.9
                )
            ]
            history = [
                ChatMessage(role="user", content="之前的问题"),
                ChatMessage(role="assistant", content="之前的回答"),
            ]

            messages = service._build_messages(
                query="新问题",
                context_docs=context_docs,
                history=history
            )

            # 验证消息结构
            assert len(messages) >= 3  # system + history + user
            assert messages[0].role == "system"
            assert messages[-1].role == "user"
            assert messages[-1].content == "新问题"

    def test_rag_service_search_only(self):
        """测试仅搜索功能"""
        from app.llm.core.rag_service import RAGService
        from app.llm.core.vector_store import VectorStore
        from app.llm.core.document_processor import DocumentChunk

        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStore(index_dir=Path(tmpdir))
            vector_store.load()

            # 添加文档
            chunks = [
                DocumentChunk(
                    content="乒乓球技术训练方法",
                    source="training.md",
                    chunk_index=0
                )
            ]
            vector_store.add_documents(chunks)

            # Mock LLM client
            mock_client = MagicMock()
            service = RAGService(
                vector_store=vector_store,
                llm_client=mock_client
            )

            results = service.search_only("乒乓球训练", top_k=5)
            assert len(results) > 0


# ========== Prompt 模板测试 ==========

class TestPromptTemplates:
    """Prompt 模板测试"""

    def test_prompt_templates_import(self):
        """测试 Prompt 模板导入"""
        from app.llm.core.prompt_templates import (
            build_system_message,
            build_context_message,
            extract_sources
        )
        assert build_system_message is not None
        assert build_context_message is not None
        assert extract_sources is not None

    def test_build_system_message(self):
        """测试系统消息构建"""
        from app.llm.core.prompt_templates import build_system_message

        # 有 RAG 上下文
        msg_with_rag = build_system_message(use_rag=True)
        assert isinstance(msg_with_rag, str)
        assert len(msg_with_rag) > 0

        # 无 RAG 上下文
        msg_without_rag = build_system_message(use_rag=False)
        assert isinstance(msg_without_rag, str)

    def test_extract_sources(self):
        """测试来源提取"""
        from app.llm.core.prompt_templates import extract_sources
        from app.llm.core.vector_store import SearchResult

        results = [
            SearchResult(content="内容1", source="doc1.md", chunk_index=0, score=0.9),
            SearchResult(content="内容2", source="doc2.md", chunk_index=0, score=0.8),
            SearchResult(content="内容3", source="doc1.md", chunk_index=1, score=0.7),
        ]
        sources = extract_sources(results)
        # 应去重
        assert isinstance(sources, list)
        assert "doc1.md" in sources
        assert "doc2.md" in sources


# ========== 文档处理器测试 ==========

class TestDocumentProcessor:
    """文档处理器测试"""

    def test_document_processor_import(self):
        """测试文档处理器导入"""
        from app.llm.core.document_processor import DocumentProcessor, DocumentChunk
        assert DocumentProcessor is not None
        assert DocumentChunk is not None

    def test_document_chunk_dataclass(self):
        """测试 DocumentChunk 数据类"""
        from app.llm.core.document_processor import DocumentChunk
        chunk = DocumentChunk(
            content="测试内容",
            source="test.md",
            chunk_index=0,
            title="测试标题"
        )
        assert chunk.content == "测试内容"
        assert chunk.source == "test.md"
        assert chunk.chunk_index == 0
        assert chunk.title == "测试标题"


# ========== API 端点测试 ==========

class TestChatAPI:
    """聊天 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_search_endpoint_validation(self, client):
        """测试搜索端点参数验证"""
        # 缺少必要参数
        response = client.post("/api/llm/search", json={})
        assert response.status_code == 422

        # top_k 超出范围
        response = client.post(
            "/api/llm/search",
            json={"query": "test", "top_k": 100}
        )
        assert response.status_code == 422

    def test_chat_endpoint_validation(self, client):
        """测试聊天端点参数验证"""
        # 消息为空
        response = client.post("/api/llm/chat", json={"message": ""})
        assert response.status_code == 422

        # temperature 超出范围
        response = client.post(
            "/api/llm/chat",
            json={"message": "test", "temperature": 5.0}
        )
        assert response.status_code == 422


# ========== 会话服务测试 ==========

class TestConversationService:
    """会话服务测试"""

    def test_conversation_service_import(self):
        """测试会话服务导入"""
        from app.llm.core.conversation_service import ConversationService
        assert ConversationService is not None
