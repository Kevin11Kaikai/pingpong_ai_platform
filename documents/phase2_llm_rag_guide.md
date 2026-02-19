# Phase 2: LLM 智能学习助手

## Overview

LLM 智能学习助手是平台的核心对话模块，基于 RAG（Retrieval-Augmented Generation）架构，用户可以上传乒乓球知识文档，通过自然语言问答获得带知识库引用的专业回答。支持流式输出、对话历史管理和知识库搜索。

---

## 目录

1. [模块架构](#1-模块架构)
2. [数据模型](#2-数据模型)
3. [RAG 管线](#3-rag-管线)
4. [核心服务](#4-核心服务)
5. [API 接口](#5-api-接口)
6. [Prompt 模板](#6-prompt-模板)
7. [使用指南](#7-使用指南)
8. [技术决策](#8-技术决策)

---

## 1. 模块架构

### 1.1 目录结构

```
app/llm/
├── __init__.py
├── models.py                    # SQLAlchemy ORM 模型（Conversation, Message, Document）
├── schemas.py                   # Pydantic 请求/响应模式
├── api/                         # REST API 路由
│   ├── __init__.py              # Router 聚合 + 模块健康检查
│   ├── chat.py                  # 对话接口（普通 + 流式 + 搜索）
│   ├── conversations.py         # 会话 CRUD
│   └── documents.py             # 知识库文档管理
└── core/                        # 核心业务逻辑
    ├── __init__.py              # 服务导出
    ├── llm_client.py            # OpenAI API 客户端封装
    ├── rag_service.py           # RAG 管线（检索 + 生成）
    ├── vector_store.py          # FAISS 向量存储
    ├── conversation_service.py  # 会话持久化服务
    ├── document_processor.py    # 文档分块处理
    └── prompt_templates.py      # 提示词模板

app/vectorstore/                 # FAISS 索引持久化目录
├── faiss_index.bin              # FAISS 二进制索引（运行时生成）
└── metadata.json                # 文档块元数据
```

### 1.2 核心组件关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM 模块架构                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────┐   ┌──────────────┐   ┌──────────────┐              │
│   │ chat.py  │   │conversations │   │ documents.py │              │
│   │ POST/chat│   │  CRUD API    │   │ 上传/索引管理 │              │
│   └────┬─────┘   └──────┬───────┘   └──────┬───────┘              │
│        │                │                   │                      │
│   ┌────▼────────────────▼───────────────────▼──────────────┐       │
│   │                     Core 服务层                          │       │
│   │                                                        │       │
│   │  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │       │
│   │  │ RAGService  │  │Conversation  │  │  Document    │  │       │
│   │  │ (检索+生成)  │  │  Service     │  │  Processor   │  │       │
│   │  └──────┬──────┘  └──────────────┘  └──────┬───────┘  │       │
│   │         │                                   │          │       │
│   │  ┌──────▼──────┐  ┌──────────────┐         │          │       │
│   │  │  LLMClient  │  │ VectorStore  │ ◄───────┘          │       │
│   │  │ (OpenAI API)│  │  (FAISS)     │                    │       │
│   │  └─────────────┘  └──────────────┘                    │       │
│   └────────────────────────────────────────────────────────┘       │
│                          │                                         │
│              ┌───────────┼───────────┐                             │
│              ▼           ▼           ▼                             │
│        ┌──────────┐ ┌────────┐ ┌──────────────┐                   │
│        │ OpenAI   │ │ FAISS  │ │   SQLite     │                   │
│        │ API 云端  │ │ 索引   │ │ (会话/文档)   │                   │
│        └──────────┘ └────────┘ └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 数据流概览

**对话请求流程：**

```
用户输入 "正手拉球的要点？"
    ↓
chat.py 接收 ChatRequest
    ↓
ConversationService: 获取/创建会话 → 保存用户消息
    ↓
RAGService.generate_with_context():
    ├─ VectorStore.search(): FAISS 相似度搜索 → top_k 相关文档块
    ├─ build_messages(): 系统提示 + 知识库上下文 + 对话历史 + 用户问题
    └─ LLMClient.chat_completion(): 调用 OpenAI API 生成回答
    ↓
ConversationService: 保存 AI 回复 + 更新会话标题
    ↓
返回 ChatResponse（回答 + 来源引用 + token 用量）
```

**文档上传流程：**

```
用户上传文档（text/markdown/txt）
    ↓
documents.py 接收 DocumentUploadRequest
    ↓
DocumentProcessor.process_document():
    ├─ clean_text(): 清理空白、控制字符
    ├─ compute_hash(): SHA256 去重检查
    └─ chunk_text(): 滑动窗口分块（1000 字符，200 重叠）
    ↓
VectorStore.add_documents():
    ├─ EmbeddingService.encode(): 文本 → 384 维向量
    ├─ FAISS index.add(): 添加到索引
    └─ save(): 持久化索引和元数据到磁盘
    ↓
Document 元数据保存到 SQLite
```

---

## 2. 数据模型

### 2.1 SQLAlchemy ORM 模型 (models.py)

**Conversation（会话）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) PK | UUID 主键 |
| `user_id` | String(100) | 用户标识（可选） |
| `title` | String(200) | 会话标题（首条消息自动生成） |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 最后更新时间 |
| `messages` | relationship | 一对多关联 Message（级联删除） |

**Message（消息）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) PK | UUID 主键 |
| `conversation_id` | String(36) FK | 关联会话 |
| `role` | String(20) | `"user"` 或 `"assistant"` |
| `content` | Text | 消息内容 |
| `tokens_used` | Integer | 该消息消耗的 token 数 |
| `created_at` | DateTime | 创建时间 |

**Document（文档）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) PK | UUID 主键 |
| `source` | String(500) UNIQUE | 文档来源标识（文件名/URL） |
| `title` | String(200) | 文档标题 |
| `content_hash` | String(64) | SHA256 内容哈希（去重用） |
| `chunk_count` | Integer | 分块数量 |
| `created_at` | DateTime | 首次上传时间 |
| `updated_at` | DateTime | 最近更新时间 |

### 2.2 Pydantic 请求/响应模式 (schemas.py)

**对话相关：**

```python
class ChatRequest(BaseModel):
    message: str                          # 用户消息
    conversation_id: Optional[str]        # 会话 ID（为空则创建新会话）
    use_rag: bool = True                  # 是否启用 RAG
    stream: bool = False                  # 是否流式输出
    temperature: float = 0.7             # 生成温度
    model: Optional[str] = None           # 模型名（默认 gpt-4o-mini）

class ChatResponse(BaseModel):
    message: str                          # AI 回复内容
    conversation_id: str                  # 会话 ID
    sources: Optional[list[str]]          # 引用来源列表
    tokens_used: Optional[int]            # 消耗 token 数
```

**知识库搜索：**

```python
class SearchRequest(BaseModel):
    query: str                            # 搜索问题
    top_k: int = 5                        # 返回前 k 个结果

class SearchResultItem(BaseModel):
    content: str                          # 文档块内容
    source: str                           # 来源标识
    score: float                          # 相似度分数
    chunk_index: int                      # 块序号
```

---

## 3. RAG 管线

### 3.1 RAG 架构详解

RAG（Retrieval-Augmented Generation）将知识库检索与 LLM 生成结合，让模型回答时可以引用具体文档内容，而非纯靠训练数据"编造"。

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG 管线流程                               │
│                                                             │
│  用户问题: "正手拉球的要点？"                                  │
│      │                                                      │
│      ▼                                                      │
│  ┌──────────────────┐                                       │
│  │ 1. Retrieval     │                                       │
│  │    (检索阶段)     │                                       │
│  │                  │                                       │
│  │  问题 → Embedding → FAISS 相似度搜索                      │
│  │       384 维向量     cosine similarity                    │
│  │                  │                                       │
│  │  返回 top_k=5 个最相关文档块                               │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                       │
│  │ 2. Augmentation  │                                       │
│  │    (增强阶段)     │                                       │
│  │                  │                                       │
│  │  将检索到的文档块拼接为"参考资料"                            │
│  │  + 系统提示词（乒乓球专家身份）                              │
│  │  + 对话历史（最近 10 轮）                                  │
│  │  + 用户原始问题                                           │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                       │
│  │ 3. Generation    │                                       │
│  │    (生成阶段)     │                                       │
│  │                  │                                       │
│  │  OpenAI API (gpt-4o-mini)                                │
│  │  根据参考资料 + 问题生成回答                                │
│  │  支持流式 / 非流式输出                                     │
│  └────────┬─────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  带来源引用的专业回答                                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Embedding 与 FAISS

**Embedding 模型：** `sentence-transformers/all-MiniLM-L6-v2`

| 属性 | 值 |
|------|-----|
| 维度 | 384 |
| 模型大小 | ~90MB |
| 语言支持 | 多语言（含中文） |
| GPU 占用 | ~0.5GB（可 CPU 运行） |
| 全模块共享 | LLM、Equipment、Social Media 复用同一实例 |

**FAISS 索引：** `IndexFlatIP`（内积，等价于余弦相似度配合 L2 归一化）

| 属性 | 值 |
|------|-----|
| 索引类型 | Flat（精确搜索，适合小规模数据） |
| 相似度 | Inner Product（向量归一化后等价 cosine） |
| 存储 | CPU 模式（GPU 留给 CV 模块） |
| 持久化 | `app/vectorstore/faiss_index.bin` + `metadata.json` |

---

## 4. 核心服务

### 4.1 LLMClient (llm_client.py)

封装 OpenAI 兼容 API 的调用，支持流式和非流式。

| 方法 | 说明 |
|------|------|
| `chat_completion(messages, stream, temperature, model)` | 通用对话补全 |
| `chat_completion_with_tokens(messages, ...)` | 返回内容 + token 用量 |
| `_regular_completion()` | 非流式实现：等待完整响应 |
| `_stream_completion()` | 流式实现：逐 chunk 生成 |

**配置：** 从 `config/settings.py` 读取 `llm_api_key` 和 `llm_base_url`，默认模型 `gpt-4o-mini`。

**单例访问：** `get_llm_client()` 通过 `@lru_cache` 保证全局唯一。

### 4.2 RAGService (rag_service.py)

编排检索和生成的完整管线。

| 方法 | 说明 |
|------|------|
| `generate_with_context(query, history, top_k, use_rag, model, temperature, stream)` | 完整 RAG 管线 |
| `search_only(query, top_k)` | 仅检索，不调 LLM |
| `_build_messages(query, context_results, history)` | 构建消息列表 |
| `_generate(messages)` | 非流式生成，返回 `RAGResponse` |
| `_stream_generate(messages)` | 流式生成，返回 async generator |

**RAGResponse 数据类：**

```python
@dataclass
class RAGResponse:
    content: str                  # LLM 回复内容
    sources: list[str]            # 引用来源列表
    tokens_used: Optional[int]    # token 消耗
```

### 4.3 VectorStore (vector_store.py)

FAISS 向量索引的封装，提供增删查和持久化。

| 方法 | 说明 |
|------|------|
| `load()` | 从磁盘加载索引和元数据，不存在则创建空索引 |
| `save()` | 持久化到 `app/vectorstore/` |
| `add_documents(chunks)` | 文档块 → Embedding → 添加到索引 |
| `search(query, top_k, threshold)` | 相似度搜索，返回 `SearchResult` 列表 |
| `delete_by_source(source)` | 按来源删除（重建索引） |
| `get_stats()` | 返回索引统计（总块数、来源数） |
| `clear()` | 清空索引 |

**ChunkMetadata 数据类：**

```python
@dataclass
class ChunkMetadata:
    source: str          # 文档来源
    content: str         # 原始文本
    chunk_index: int     # 在文档中的块序号
    title: str           # 文档标题
```

### 4.4 ConversationService (conversation_service.py)

会话和消息的数据库持久化服务。

| 方法 | 说明 |
|------|------|
| `create_conversation(title, user_id)` | 创建会话 |
| `get_conversation(id)` | 获取会话（含消息 eager load） |
| `list_conversations(user_id, skip, limit)` | 分页列表 |
| `delete_conversation(id)` | 删除会话（级联删除消息） |
| `add_message(conversation_id, role, content, tokens_used)` | 添加消息 |
| `get_chat_history(conversation_id, limit)` | 获取最近 N 轮历史 |
| `update_title(conversation_id, title)` | 更新标题 |

### 4.5 DocumentProcessor (document_processor.py)

文档预处理和分块。

| 方法 | 说明 |
|------|------|
| `clean_text(text)` | 清理空白、控制字符、多余换行 |
| `chunk_text(text, chunk_size, overlap)` | 滑动窗口分块，优先在句子边界断开 |
| `compute_hash(content)` | SHA256 内容哈希（用于去重） |
| `process_document(content, source, title)` | 完整管线：清理 → 哈希 → 分块 |

**分块策略：**

- 默认块大小: 1000 字符，重叠 200 字符
- 优先在句子边界断开（支持中英文句号 `.` `。`、问号 `?` `？`、感叹号 `!` `！`）
- 如果找不到句子边界，在块大小处硬切

---

## 5. API 接口

### 5.1 对话接口 (chat.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/llm/chat` | POST | 普通对话（RAG 增强） |
| `/api/llm/chat/stream` | POST | 流式对话（SSE） |
| `/api/llm/search` | POST | 知识库搜索（仅检索） |

**POST /api/llm/chat 请求示例：**

```json
{
  "message": "正手拉球的要点是什么？",
  "conversation_id": null,
  "use_rag": true,
  "temperature": 0.7
}
```

**响应示例：**

```json
{
  "message": "正手拉球的核心要点包括：\n1. 站位：...\n2. 引拍：...\n3. 发力：...",
  "conversation_id": "cc188ebe-7f31-4277-856e-e4fad278a3d8",
  "sources": ["正手技术教程.pdf"],
  "tokens_used": 474
}
```

**POST /api/llm/chat/stream** 返回 Server-Sent Events（SSE）：

```
data: 正手
data: 拉球
data: 的核心
data: 要点
...
data: [DONE]
```

### 5.2 会话管理 (conversations.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/llm/conversations` | POST | 创建会话 |
| `/api/llm/conversations` | GET | 会话列表（分页，支持 user_id 过滤） |
| `/api/llm/conversations/{id}` | GET | 会话详情（含消息列表） |
| `/api/llm/conversations/{id}` | PATCH | 更新标题 |
| `/api/llm/conversations/{id}` | DELETE | 删除会话（级联删除消息） |

### 5.3 知识库管理 (documents.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/llm/documents` | POST | 上传文档（自动分块 + 索引） |
| `/api/llm/documents` | GET | 文档列表 |
| `/api/llm/documents/{source}` | DELETE | 按来源删除文档 |
| `/api/llm/documents/rebuild-index` | POST | 重建向量索引 |
| `/api/llm/documents/stats` | GET | 索引统计 |

**POST /api/llm/documents 请求示例：**

```json
{
  "content": "正手拉球是乒乓球最基本也最重要的进攻技术...",
  "source": "正手技术教程.pdf",
  "title": "正手拉球教程"
}
```

**特性：**
- 内容哈希去重：相同内容不会重复索引
- 支持更新：同一 source 再次上传会替换旧内容
- 原子操作：上传失败不会留下脏数据

### 5.4 模块健康检查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/llm/health` | GET | `{"module":"llm","status":"healthy"}` |

---

## 6. Prompt 模板

### 6.1 prompt_templates.py

**系统提示词 (PINGPONG_SYSTEM_PROMPT)：**

定义 AI 的身份为"乒乓球专业教练和技术顾问"，指导其：
- 基于知识库资料回答，标注来源
- 对技术动作给出详细步骤
- 无相关资料时诚实说明
- 使用中文回答

**RAG 上下文模板 (RAG_CONTEXT_TEMPLATE)：**

```
以下是与用户问题相关的参考资料：

[来源: 正手技术教程.pdf]
正手拉球是乒乓球最基本也最重要的进攻技术...

[来源: 步法训练指南.pdf]
正手拉球的步法要求...

请基于以上参考资料回答用户的问题。如果参考资料中没有相关信息，请说明。
```

### 6.2 消息构建流程

```python
messages = [
    {"role": "system", "content": system_prompt + rag_context},
    # 对话历史（最近 10 轮）
    {"role": "user", "content": "上次提到的正手..."},
    {"role": "assistant", "content": "是的，关于正手..."},
    # 当前问题
    {"role": "user", "content": "那反手呢？"},
]
```

---

## 7. 使用指南

### 7.1 添加知识库文档

```bash
# 上传文档
curl -X POST http://localhost:8000/api/llm/documents \
  -H "Content-Type: application/json" \
  -d '{"content":"乒乓球正手拉球技术要点...","source":"forehand.pdf","title":"正手拉球"}'

# 查看索引统计
curl http://localhost:8000/api/llm/documents/stats
```

### 7.2 对话问答

```bash
# 普通对话（自动创建会话）
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"正手拉球的要点？","conversation_id":null}'

# 继续对话（传入 conversation_id）
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"步法怎么配合？","conversation_id":"上次返回的id"}'

# 不使用 RAG（纯 LLM 回答）
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","use_rag":false}'
```

### 7.3 知识库搜索

```bash
# 仅搜索，不调 LLM
curl -X POST http://localhost:8000/api/llm/search \
  -H "Content-Type: application/json" \
  -d '{"query":"如何提高发球质量","top_k":5}'
```

---

## 8. 技术决策

### 8.1 为什么用云端 LLM 而不是本地模型？

| 方案 | GPU 占用 | 中文质量 | 延迟 | 成本 |
|------|----------|----------|------|------|
| **gpt-4o-mini (云端)** | 0 GB | 优秀 | ~1s 首 token | ~$0.15/1M tokens |
| Llama 3 8B (本地) | ~8 GB | 一般 | ~2s 首 token | 免费 |
| Qwen 7B (本地) | ~8 GB | 良好 | ~2s 首 token | 免费 |

选择云端原因：16GB GPU 需要留给 CV 模块（BlurBall ~6GB + RTMPose ~2GB），同时跑本地 LLM 会导致 OOM。

### 8.2 为什么用 FAISS 而不是其他向量数据库？

| 方案 | 优势 | 劣势 |
|------|------|------|
| **FAISS (CPU)** | 零额外服务、嵌入式、速度快 | 不支持分布式 |
| ChromaDB | 易用、自动持久化 | 额外进程 |
| Milvus/Weaviate | 分布式、高可用 | 太重，单机过度设计 |

本项目知识库规模小（百~千条文档块），FAISS CPU 模式完全够用，且不需要额外进程。

### 8.3 为什么用 sentence-transformers 而不是 OpenAI Embedding？

| 方案 | 维度 | 速度 | 成本 | 离线可用 |
|------|------|------|------|----------|
| **all-MiniLM-L6-v2** | 384 | ~5ms/句 | 免费 | 是 |
| text-embedding-3-small | 1536 | ~100ms/句 | $0.02/1M tokens | 否 |

选择本地 Embedding 原因：免费、低延迟、离线可用，且 384 维对小规模检索足够准确。模型 ~90MB，常驻 CPU 不占 GPU。
