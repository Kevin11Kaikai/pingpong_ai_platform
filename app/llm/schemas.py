"""
LLM 模块 Pydantic Schema
定义所有 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ========== 聊天相关 Schema ==========

class ChatMessage(BaseModel):
    """聊天消息"""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=10000, description="用户消息")
    conversation_id: Optional[str] = Field(None, description="会话ID，不传则创建新会话")
    use_rag: bool = Field(True, description="是否使用RAG检索")
    stream: bool = Field(False, description="是否流式输出")
    temperature: float = Field(0.7, ge=0, le=2, description="生成温度")
    model: str = Field("gpt-4o-mini", description="模型名称")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str
    conversation_id: str
    sources: Optional[List[str]] = Field(None, description="RAG 引用的文档来源")
    tokens_used: Optional[int] = None


# ========== 会话管理 Schema ==========

class ConversationCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = Field(None, max_length=255)
    user_id: Optional[str] = None


class ConversationUpdate(BaseModel):
    """更新会话请求"""
    title: str = Field(..., max_length=255)


class ConversationResponse(BaseModel):
    """会话响应"""
    id: str
    title: Optional[str]
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """会话列表响应"""
    conversations: List[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    role: str
    content: str
    tokens_used: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """会话详情响应（含消息）"""
    id: str
    title: Optional[str]
    user_id: Optional[str]
    messages: List[MessageResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 文档管理 Schema ==========

class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    content: str = Field(..., min_length=10, description="文档内容")
    source: str = Field(..., description="来源标识")
    title: Optional[str] = None


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    source: str
    title: Optional[str]
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[DocumentResponse]
    total: int


# ========== 搜索 Schema ==========

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)


class SearchResultItem(BaseModel):
    """搜索结果项"""
    content: str
    source: str
    score: float
    chunk_index: int


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResultItem]
    query: str
