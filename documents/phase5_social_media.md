# Phase 5: Social Media Module

## Overview

社交媒体问答模块为用户提供乒乓球相关社交媒体内容的抓取、分析和智能回复功能。基于 LLM 进行内容分析，使用 RAG 技术生成高质量回复建议。

---

## 目录

1. [模块架构](#1-模块架构)
2. [数据模型](#2-数据模型)
3. [核心服务](#3-核心服务)
4. [API 接口](#4-api-接口)
5. [抓取框架](#5-抓取框架)
6. [复用组件](#6-复用组件)
7. [测试方案](#7-测试方案)
8. [使用指南](#8-使用指南)
9. [常见问题](#9-常见问题)

---

## 1. 模块架构

### 1.1 目录结构

```
app/social_media/
├── __init__.py              # 模块导出
├── models.py                # SQLAlchemy ORM 数据库模型 (6 个表)
├── schemas.py               # Pydantic 请求/响应模式 (~25 个类)
├── core/                    # 核心业务逻辑
│   ├── __init__.py
│   ├── content_service.py   # 内容 CRUD 和搜索
│   ├── analysis_service.py  # LLM 内容分析
│   ├── reply_service.py     # RAG 回复生成
│   └── scraper_service.py   # 抓取服务框架
└── api/                     # REST API 路由
    ├── __init__.py          # Router 聚合
    ├── contents.py          # 内容管理 API
    ├── analysis.py          # 内容分析 API
    ├── replies.py           # 回复建议 API
    └── scrape.py            # 抓取任务 API
```

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Social Media Module 架构                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│   │   API 层    │    │   API 层    │    │   API 层    │             │
│   │  contents   │    │  analysis   │    │   replies   │             │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│          │                  │                  │                     │
│          ▼                  ▼                  ▼                     │
│   ┌─────────────────────────────────────────────────────┐           │
│   │                    Core 服务层                       │           │
│   │  ┌───────────────┐  ┌───────────────┐              │           │
│   │  │ContentService │  │AnalysisService│              │           │
│   │  │  - CRUD 操作   │  │  - LLM 分析   │              │           │
│   │  │  - 语义搜索   │  │  - 主题提取   │              │           │
│   │  └───────────────┘  └───────────────┘              │           │
│   │  ┌───────────────┐  ┌───────────────┐              │           │
│   │  │ ReplyService  │  │ScraperService │              │           │
│   │  │  - RAG 回复   │  │  - 平台抓取   │              │           │
│   │  │  - 质量评估   │  │  - 内容解析   │              │           │
│   │  └───────────────┘  └───────────────┘              │           │
│   └─────────────────────────────────────────────────────┘           │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────┐           │
│   │                    复用组件层                        │           │
│   │  EmbeddingService + LLMClient + RAGService          │           │
│   └─────────────────────────────────────────────────────┘           │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────┐           │
│   │                    数据层                            │           │
│   │  SQLite + SQLAlchemy Async                          │           │
│   └─────────────────────────────────────────────────────┘           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据模型

### 2.1 枚举类型

#### Platform (社交媒体平台)

| 值 | 说明 |
|------|------|
| zhihu | 知乎 |
| weibo | 微博 |
| tieba | 贴吧 |
| douyin | 抖音评论区 |
| xiaohongshu | 小红书 |
| bilibili | B站评论区 |
| reddit | Reddit |
| custom | 自定义来源 |

#### ContentType (内容类型)

| 值 | 说明 |
|------|------|
| question | 问题/提问 |
| answer | 回答 |
| post | 帖子/文章 |
| comment | 评论 |
| thread | 讨论串 |

#### ContentStatus (内容状态)

| 值 | 说明 |
|------|------|
| pending | 待处理 |
| analyzed | 已分析 |
| replied | 已生成回复 |
| published | 已发布 |
| archived | 已归档 |

### 2.2 SocialPlatformConfig (平台配置)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| platform | Enum | 平台类型 (unique) |
| display_name | String(100) | 平台显示名 |
| base_url | String(512) | 平台基础 URL |
| scrape_enabled | Boolean | 是否启用抓取 |
| scrape_interval_minutes | Integer | 抓取间隔（分钟） |
| scrape_keywords | JSON | 关键词列表 |
| scrape_max_items | Integer | 单次最大抓取数 |
| auth_config | JSON | 认证配置（加密） |
| rate_limit_per_minute | Integer | 每分钟请求限制 |
| is_active | Boolean | 是否启用 |

### 2.3 ScrapeTask (抓取任务)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| platform_config_id | FK | 平台配置 ID |
| keywords | JSON | 本次任务关键词 |
| target_url | String(1024) | 指定抓取 URL |
| status | String(20) | pending/running/completed/failed |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |
| items_found | Integer | 发现数量 |
| items_saved | Integer | 保存数量 |
| error_message | Text | 错误信息 |

### 2.4 SocialContent (社交内容)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| platform_config_id | FK | 平台配置 ID |
| external_id | String(255) | 平台原始 ID |
| external_url | String(1024) | 原始链接 |
| content_type | Enum | 内容类型 |
| title | String(500) | 标题 |
| content | Text | 正文内容 |
| author_name | String(255) | 作者名 |
| author_id | String(255) | 作者 ID |
| parent_id | FK | 父级内容 ID |
| view_count | Integer | 浏览数 |
| like_count | Integer | 点赞数 |
| comment_count | Integer | 评论数 |
| share_count | Integer | 分享数 |
| published_at | DateTime | 原始发布时间 |
| tags | JSON | 标签列表 |
| status | Enum | 处理状态 |
| quality_score | Float | 质量评分 (0-1) |
| relevance_score | Float | 相关度 (0-1) |
| embedding | JSON | 向量嵌入 (384维) |
| analysis_result | JSON | 分析结果 |

### 2.5 ContentTag (内容标签)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(100) | 标签名 (unique) |
| display_name | String(100) | 显示名称 |
| category | String(50) | 标签分类 |
| description | Text | 描述 |
| usage_count | Integer | 使用次数 |
| embedding | JSON | 向量嵌入 |

### 2.6 ContentTagMapping (内容-标签关联)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| content_id | FK | 内容 ID |
| tag_id | FK | 标签 ID |
| confidence | Float | 标签置信度 |
| source | String(50) | manual/auto/ai |

### 2.7 ReplySuggestion (回复建议)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| content_id | FK | 内容 ID |
| reply_content | Text | 回复内容 |
| model_used | String(50) | 使用的模型 |
| temperature | Float | 生成温度 |
| style | String(50) | 回复风格 |
| sources | JSON | RAG 引用来源 |
| quality_score | Float | 质量评分 |
| is_selected | Boolean | 是否被选中 |
| is_published | Boolean | 是否已发布 |
| user_feedback | String(20) | helpful/not_helpful/edited |
| edited_content | Text | 编辑后的内容 |

---

## 3. 核心服务

### 3.1 ContentService (内容服务)

**职责**: 内容的 CRUD 操作和搜索功能

**关键方法**:

| 方法 | 说明 |
|------|------|
| `create_content(db, data)` | 创建内容，自动生成向量嵌入 |
| `get_content(db, content_id)` | 获取内容详情 |
| `update_content(db, content_id, data)` | 更新内容，内容变化时重新生成嵌入 |
| `delete_content(db, content_id)` | 删除内容及关联数据 |
| `search_contents(db, params)` | 多条件筛选搜索 |
| `semantic_search(db, params)` | 基于向量的语义搜索 |
| `get_stats(db)` | 获取统计信息 |

### 3.2 AnalysisService (分析服务)

**职责**: 使用 LLM 分析内容，提取主题、情感、关键点

**关键方法**:

| 方法 | 说明 |
|------|------|
| `analyze_content(db, content_id, force)` | 分析单个内容 |
| `batch_analyze(db, content_ids, status, limit)` | 批量分析 |

**分析输出**:
```json
{
  "topics": ["发球", "旋转"],
  "question_type": "technique",
  "difficulty_level": "beginner",
  "sentiment": "neutral",
  "key_points": ["要点1", "要点2"],
  "suggested_tags": ["技术", "入门"],
  "quality_score": 0.8,
  "relevance_score": 0.9
}
```

### 3.3 ReplyService (回复服务)

**职责**: 基于 RAG 生成高质量回复建议

**关键方法**:

| 方法 | 说明 |
|------|------|
| `generate_reply(db, content_id, style, use_rag, ...)` | 生成回复建议 |
| `get_suggestions(db, content_id)` | 获取建议列表 |
| `get_suggestion(db, suggestion_id)` | 获取单个建议 |
| `submit_feedback(db, suggestion_id, feedback, edited)` | 提交反馈 |
| `mark_published(db, suggestion_id)` | 标记已发布 |

**回复风格**:

| 风格 | 说明 |
|------|------|
| professional | 专业教练风格，有条理，引用技术要点 |
| friendly | 热心球友风格，亲切口语化，分享经验 |
| concise | 简洁专家风格，直击要点，200字以内 |

### 3.4 ScraperService (抓取服务)

**职责**: 管理各平台抓取器的调度和执行

**关键方法**:

| 方法 | 说明 |
|------|------|
| `create_task(db, platform, keywords, url)` | 创建抓取任务 |
| `execute_task(db, task_id)` | 执行抓取任务 |
| `get_task(db, task_id)` | 获取任务详情 |
| `list_tasks(db, platform, status, limit)` | 任务列表 |
| `get_scraper(platform, config)` | 获取平台抓取器 |

---

## 4. API 接口

### 4.1 内容管理 (`/api/social-media/contents`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | / | 创建内容（手动导入） |
| GET | /stats | 获取统计信息 |
| GET | /{content_id} | 获取内容详情 |
| PUT | /{content_id} | 更新内容 |
| DELETE | /{content_id} | 删除内容 |
| POST | /search | 多条件搜索 |
| POST | /semantic-search | 语义搜索 |

### 4.2 内容分析 (`/api/social-media/analysis`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /analyze | 分析单个内容 |
| POST | /batch-analyze | 批量分析（后台执行） |

### 4.3 回复建议 (`/api/social-media/replies`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /generate | 生成回复建议 |
| GET | /content/{content_id} | 获取内容的建议列表 |
| GET | /{suggestion_id} | 获取单个建议 |
| POST | /feedback | 提交反馈 |
| POST | /publish | 标记已发布 |

### 4.4 内容抓取 (`/api/social-media/scrape`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /tasks | 创建抓取任务 |
| GET | /tasks/{task_id} | 获取任务状态 |
| GET | /tasks | 任务列表 |
| GET | /platforms | 平台配置列表 |
| POST | /platforms | 创建平台配置 |
| PUT | /platforms/{platform} | 更新平台配置 |

### 4.5 健康检查 (`/api/social-media`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 模块健康检查 |

---

## 5. 抓取框架

### 5.1 抓取器基类

```python
class BaseScraper(ABC):
    """抓取器基类"""

    @abstractmethod
    async def scrape(self, keywords: List[str], max_items: int) -> List[Dict]:
        """执行关键词搜索抓取"""
        pass

    @abstractmethod
    async def scrape_url(self, url: str) -> List[Dict]:
        """抓取指定 URL"""
        pass

    @abstractmethod
    def parse_content(self, raw_data: Dict) -> Dict:
        """解析原始数据为标准格式"""
        pass
```

### 5.2 知乎抓取器示例

```python
class ZhihuScraper(BaseScraper):
    """知乎抓取器示例"""

    async def scrape(self, keywords, max_items):
        # TODO: 实现知乎搜索 API 调用
        # 需要处理反爬机制、速率限制
        pass

    def parse_content(self, raw_data):
        return {
            "external_id": raw_data.get("id"),
            "external_url": raw_data.get("url"),
            "content_type": "question" if raw_data.get("type") == "question" else "answer",
            "title": raw_data.get("title"),
            "content": raw_data.get("content"),
            "author_name": raw_data.get("author", {}).get("name"),
            "like_count": raw_data.get("voteup_count", 0),
            "comment_count": raw_data.get("comment_count", 0),
        }
```

### 5.3 扩展新平台

1. 创建新抓取器类，继承 `BaseScraper`
2. 实现三个抽象方法
3. 在 `ScraperService.SCRAPER_CLASSES` 中注册

```python
# 1. 创建抓取器
class WeiboScraper(BaseScraper):
    async def scrape(self, keywords, max_items):
        # 实现微博搜索
        pass

    async def scrape_url(self, url):
        # 实现微博页面抓取
        pass

    def parse_content(self, raw_data):
        # 解析微博内容格式
        pass

# 2. 注册到服务
class ScraperService:
    SCRAPER_CLASSES = {
        Platform.ZHIHU: ZhihuScraper,
        Platform.WEIBO: WeiboScraper,  # 添加这行
    }
```

---

## 6. 复用组件

### 6.1 EmbeddingService

**路径**: `app/shared/embedding_service.py`

**用途**: 生成内容向量嵌入，用于语义搜索

```python
from app.shared.embedding_service import EmbeddingService

# 单条文本向量化
embedding = EmbeddingService.encode_single("乒乓球正手发球技术")
# 返回: np.ndarray, shape=(384,)

# 批量向量化
embeddings = EmbeddingService.encode(["文本1", "文本2"])
# 返回: np.ndarray, shape=(2, 384)
```

### 6.2 LLMClient

**路径**: `app/llm/core/llm_client.py`

**用途**: 调用 OpenAI API 进行内容分析

```python
from app.llm.core.llm_client import get_llm_client
from app.llm.schemas import ChatMessage

client = get_llm_client()
response = await client.chat_completion(
    messages=[ChatMessage(role="user", content="分析这段内容...")],
    model="gpt-4o-mini",
    temperature=0.3,
)
```

### 6.3 RAGService

**路径**: `app/llm/core/rag_service.py`

**用途**: 使用 RAG 技术生成回复

```python
from app.llm.core.rag_service import get_rag_service

rag_service = get_rag_service()
response = await rag_service.generate_with_context(
    query="如何改进正手发球？",
    use_rag=True,
    top_k=5,
    model="gpt-4o-mini",
    temperature=0.7,
)
# response.content: 生成的回复
# response.sources: 引用的文档来源
```

---

## 7. 测试方案

### 7.1 运行测试

```bash
# 运行所有社交媒体模块测试
pytest tests/test_social_media.py -v

# 仅运行单元测试（不含集成测试）
pytest tests/test_social_media.py -v -k "not Integration"

# 运行特定测试类
pytest tests/test_social_media.py::TestSchemas -v
pytest tests/test_social_media.py::TestContentService -v
```

### 7.2 测试覆盖范围

| 测试类 | 测试数量 | 覆盖内容 |
|--------|----------|----------|
| TestSchemas | 11 | Schema 验证、枚举类型、默认值 |
| TestModels | 3 | ORM 模型枚举 |
| TestContentService | 1 | 余弦相似度计算 |
| TestReplyService | 3 | 回复质量评估 |
| TestAnalysisService | 2 | 分析结果解析 |
| TestScraperService | 1 | 知乎内容解析 |
| TestContentServiceIntegration | 5 | 内容 CRUD 集成测试 |
| TestHealthAPI | 2 | 健康检查 API |
| TestContentsAPI | 10 | 内容管理 API (CRUD, 搜索) |
| TestAnalysisAPI | 2 | 内容分析 API |
| TestRepliesAPI | 5 | 回复建议 API |
| TestScrapeAPI | 9 | 抓取任务 API |
| **Total** | **54** | |

### 7.3 测试结果

```
pytest tests/test_social_media.py -v
...
=============== 53 passed, 1 skipped in 9.95s ================
```

**注意**: 1 个测试 (test_create_scrape_task_success) 因后台任务在测试环境中的 greenlet 问题被跳过。

---

## 8. 使用指南

### 8.1 快速开始

```bash
# 1. 激活环境
conda activate pingpong_ai

# 2. 安装新依赖
pip install beautifulsoup4 lxml fake-useragent tenacity

# 3. 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. 检查健康状态
curl http://localhost:8000/api/social-media/health
```

### 8.2 创建内容

```bash
curl -X POST "http://localhost:8000/api/social-media/contents" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "content_type": "question",
    "title": "如何提高正手拉球的旋转？",
    "content": "我是初学者，正手拉球总是没有旋转，请问该怎么改进？",
    "author_name": "乒乓球爱好者",
    "tags": ["正手", "旋转", "技术"]
  }'
```

### 8.3 语义搜索

```bash
curl -X POST "http://localhost:8000/api/social-media/contents/semantic-search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何练习发球旋转",
    "top_k": 5,
    "min_score": 0.3
  }'
```

### 8.4 分析内容

```bash
# 分析单个内容
curl -X POST "http://localhost:8000/api/social-media/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "your-content-id",
    "force_reanalyze": false
  }'

# 批量分析待处理内容
curl -X POST "http://localhost:8000/api/social-media/analysis/batch-analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "status_filter": "pending",
    "limit": 50
  }'
```

### 8.5 生成回复

```bash
# 生成专业风格回复
curl -X POST "http://localhost:8000/api/social-media/replies/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "your-content-id",
    "style": "professional",
    "use_rag": true,
    "max_length": 500,
    "temperature": 0.7
  }'

# 获取回复建议列表
curl "http://localhost:8000/api/social-media/replies/content/your-content-id"

# 提交反馈
curl -X POST "http://localhost:8000/api/social-media/replies/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "suggestion_id": "your-suggestion-id",
    "feedback": "helpful"
  }'
```

### 8.6 配置平台

```bash
# 创建知乎平台配置
curl -X POST "http://localhost:8000/api/social-media/scrape/platforms" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "display_name": "知乎",
    "scrape_enabled": true,
    "scrape_interval_minutes": 60,
    "scrape_keywords": ["乒乓球", "发球技术", "底板推荐"],
    "scrape_max_items": 100
  }'

# 创建抓取任务
curl -X POST "http://localhost:8000/api/social-media/scrape/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "zhihu",
    "keywords": ["乒乓球正手"]
  }'
```

---

## 9. 常见问题

### Q1: 语义搜索结果为空

**原因**:
1. 内容没有向量嵌入
2. 相似度阈值设置过高

**解决**:
1. 确保内容创建时自动生成了 embedding
2. 降低 `min_score` 参数（默认 0.3）

### Q2: 内容分析失败

**原因**:
1. LLM API 配置错误
2. 内容过长超出 token 限制

**解决**:
1. 检查 `.env` 中的 `LLM_API_KEY` 和 `LLM_BASE_URL`
2. 内容会自动截断到 2000 字符

### Q3: 回复质量评分低

**原因**:
1. 回复过短
2. 缺少乒乓球相关词汇

**解决**:
1. 增加 `max_length` 参数
2. 确保 RAG 知识库包含乒乓球相关文档

### Q4: 抓取任务状态始终为 pending

**原因**:
1. 平台抓取器未实现
2. 平台配置 `scrape_enabled` 为 false

**解决**:
1. 当前版本抓取器为框架代码，需实现具体抓取逻辑
2. 检查平台配置是否启用

### Q5: API 返回 422 错误

**原因**: 请求参数格式错误

**解决**: 检查枚举值是否正确：
- `platform`: "zhihu" | "weibo" | "tieba" | "bilibili" | ...
- `content_type`: "question" | "answer" | "post" | "comment" | "thread"
- `status`: "pending" | "analyzed" | "replied" | "published" | "archived"
- `style`: "professional" | "friendly" | "concise"
- `feedback`: "helpful" | "not_helpful" | "edited"

---

## 附录

### A. 配置参数

```python
# config/settings.py
social_media_scrape_enabled: bool = True
social_media_default_interval_minutes: int = 60
social_media_max_items_per_scrape: int = 100
social_media_analysis_batch_size: int = 50
social_media_reply_max_length: int = 500
social_media_reply_default_style: str = "professional"
```

### B. 依赖

```
# requirements.txt (Phase 5 新增)
beautifulsoup4>=4.12.0    # HTML 解析
lxml>=5.1.0               # 快速 XML/HTML 解析器
fake-useragent>=1.4.0     # User Agent 轮换
tenacity>=8.2.0           # 重试逻辑

# 复用依赖
sentence-transformers     # 向量编码 (all-MiniLM-L6-v2)
openai                    # LLM API
faiss-cpu                 # 向量搜索 (RAG)
```

### C. 分析提示模板

```
请分析以下乒乓球相关的社交媒体内容，提取关键信息。

内容类型: {content_type}
标题: {title}
内容:
---
{content}
---

请以 JSON 格式返回分析结果：
{
    "topics": ["主题1", "主题2"],
    "question_type": "technique|equipment|rule|training|other|null",
    "difficulty_level": "beginner|intermediate|advanced|null",
    "sentiment": "positive|neutral|negative",
    "key_points": ["要点1", "要点2"],
    "suggested_tags": ["标签1", "标签2"],
    "quality_score": 0.0-1.0,
    "relevance_score": 0.0-1.0
}
```

### D. 回复风格提示

**Professional (专业)**:
> 你是一位专业的乒乓球教练，回复社交媒体上的问题。
> 请用专业但易懂的语言回答，必要时引用技术要点。
> 回复要有条理，可以使用编号列表。

**Friendly (友好)**:
> 你是一位热心的乒乓球爱好者，回复社交媒体上的问题。
> 请用亲切友好的语气回答，可以分享个人经验和心得。

**Concise (简洁)**:
> 你是乒乓球专家，简洁回复问题。
> 回答要精炼，直击要点，控制在 200 字以内。
