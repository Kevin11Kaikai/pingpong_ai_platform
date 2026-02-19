"""
社交媒体问答模块 Pydantic Schema
定义所有 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ========== 枚举类型 ==========

PlatformType = Literal[
    "zhihu", "weibo", "tieba", "douyin",
    "xiaohongshu", "bilibili", "reddit", "custom"
]
ContentTypeEnum = Literal["question", "answer", "post", "comment", "thread"]
ContentStatusEnum = Literal["pending", "analyzed", "replied", "published", "archived"]
ReplyStyleType = Literal["professional", "friendly", "concise"]
FeedbackType = Literal["helpful", "not_helpful", "edited"]


# ========== 平台配置 Schema ==========

class PlatformConfigCreate(BaseModel):
    """创建平台配置请求"""
    platform: PlatformType = Field(..., description="平台标识")
    display_name: str = Field(..., min_length=1, max_length=100, description="平台显示名")
    base_url: Optional[str] = Field(None, max_length=512, description="基础 URL")
    scrape_enabled: bool = Field(True, description="是否启用抓取")
    scrape_interval_minutes: int = Field(60, ge=5, le=1440, description="抓取间隔(分钟)")
    scrape_keywords: Optional[List[str]] = Field(None, description="抓取关键词")
    scrape_max_items: int = Field(100, ge=1, le=1000, description="单次最大抓取数")
    rate_limit_per_minute: int = Field(10, ge=1, le=60, description="每分钟请求限制")


class PlatformConfigUpdate(BaseModel):
    """更新平台配置请求"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, max_length=512)
    scrape_enabled: Optional[bool] = None
    scrape_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    scrape_keywords: Optional[List[str]] = None
    scrape_max_items: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=60)
    is_active: Optional[bool] = None


class PlatformConfigResponse(BaseModel):
    """平台配置响应"""
    id: str
    platform: str
    display_name: str
    base_url: Optional[str]
    scrape_enabled: bool
    scrape_interval_minutes: int
    scrape_keywords: Optional[List[str]]
    scrape_max_items: int
    rate_limit_per_minute: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformConfigListResponse(BaseModel):
    """平台配置列表响应"""
    platforms: List[PlatformConfigResponse]
    total: int


# ========== 抓取任务 Schema ==========

class ScrapeTaskCreate(BaseModel):
    """创建抓取任务请求"""
    platform: PlatformType = Field(..., description="目标平台")
    keywords: Optional[List[str]] = Field(None, description="搜索关键词")
    target_url: Optional[str] = Field(None, max_length=1024, description="指定 URL")


class ScrapeTaskResponse(BaseModel):
    """抓取任务响应"""
    id: str
    platform: str
    keywords: Optional[List[str]]
    target_url: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    items_found: int
    items_saved: int
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScrapeTaskListResponse(BaseModel):
    """抓取任务列表响应"""
    tasks: List[ScrapeTaskResponse]
    total: int


# ========== 社交内容 Schema ==========

class ContentCreate(BaseModel):
    """创建内容请求（手动导入）"""
    platform: PlatformType = Field(..., description="来源平台")
    content_type: ContentTypeEnum = Field(..., description="内容类型")
    title: Optional[str] = Field(None, max_length=500, description="标题")
    content: str = Field(..., min_length=1, description="内容正文")
    author_name: Optional[str] = Field(None, max_length=255, description="作者名")
    external_url: Optional[str] = Field(None, max_length=1024, description="原始链接")
    external_id: Optional[str] = Field(None, max_length=255, description="原始 ID")
    published_at: Optional[datetime] = Field(None, description="原始发布时间")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class ContentUpdate(BaseModel):
    """更新内容请求"""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    status: Optional[ContentStatusEnum] = None


class ContentBrief(BaseModel):
    """内容简要信息"""
    id: str
    platform: str
    content_type: str
    title: Optional[str]
    content_preview: str  # 内容预览（截断）
    author_name: Optional[str]
    status: str
    quality_score: Optional[float]
    like_count: int
    comment_count: int
    reply_count: int  # 回复建议数量
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentResponse(BaseModel):
    """内容详情响应"""
    id: str
    platform: str
    content_type: str
    title: Optional[str]
    content: str
    author_name: Optional[str]
    author_id: Optional[str]
    external_url: Optional[str]
    external_id: Optional[str]

    parent_id: Optional[str]

    view_count: int
    like_count: int
    comment_count: int
    share_count: int

    published_at: Optional[datetime]
    tags: Optional[List[str]]
    status: str
    quality_score: Optional[float]
    relevance_score: Optional[float]
    analysis_result: Optional[Dict[str, Any]]

    reply_suggestion_count: int

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentListResponse(BaseModel):
    """内容列表响应"""
    contents: List[ContentBrief]
    total: int
    page: int
    page_size: int


class ContentSearchRequest(BaseModel):
    """内容搜索请求"""
    query: Optional[str] = Field(None, max_length=500, description="搜索关键词")
    platform: Optional[PlatformType] = Field(None, description="平台筛选")
    content_type: Optional[ContentTypeEnum] = Field(None, description="内容类型")
    status: Optional[ContentStatusEnum] = Field(None, description="状态筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    min_quality_score: Optional[float] = Field(None, ge=0, le=1, description="最低质量分")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    top_k: int = Field(10, ge=1, le=50, description="返回数量")
    platform: Optional[PlatformType] = Field(None, description="平台筛选")
    content_type: Optional[ContentTypeEnum] = Field(None, description="内容类型")
    min_score: float = Field(0.3, ge=0, le=1, description="最低相似度")


class SemanticSearchResult(BaseModel):
    """语义搜索结果项"""
    content: ContentBrief
    similarity_score: float


class SemanticSearchResponse(BaseModel):
    """语义搜索响应"""
    results: List[SemanticSearchResult]
    query: str
    total: int


# ========== 内容分析 Schema ==========

class ContentAnalysisRequest(BaseModel):
    """内容分析请求"""
    content_id: str = Field(..., description="内容 ID")
    force_reanalyze: bool = Field(False, description="强制重新分析")


class ContentAnalysisResponse(BaseModel):
    """内容分析响应"""
    content_id: str
    topics: List[str]
    question_type: Optional[str]  # technique, equipment, rule, training, other
    difficulty_level: Optional[str]  # beginner, intermediate, advanced
    sentiment: str  # positive, neutral, negative
    key_points: List[str]
    suggested_tags: List[str]
    quality_score: float
    relevance_score: float


class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    content_ids: Optional[List[str]] = Field(None, description="指定内容 ID 列表")
    status_filter: Optional[ContentStatusEnum] = Field("pending", description="状态筛选")
    limit: int = Field(50, ge=1, le=200, description="处理数量")


class BatchAnalysisResponse(BaseModel):
    """批量分析响应"""
    task_id: str
    total_queued: int
    message: str


# ========== 回复建议 Schema ==========

class ReplyGenerateRequest(BaseModel):
    """生成回复请求"""
    content_id: str = Field(..., description="内容 ID")
    style: ReplyStyleType = Field("professional", description="回复风格")
    use_rag: bool = Field(True, description="是否使用 RAG 检索")
    max_length: int = Field(500, ge=50, le=2000, description="最大长度")
    temperature: float = Field(0.7, ge=0, le=1, description="生成温度")


class ReplySuggestionResponse(BaseModel):
    """回复建议响应"""
    id: str
    content_id: str
    reply_content: str
    style: str
    model_used: str
    sources: Optional[List[str]]
    quality_score: Optional[float]
    is_selected: bool
    is_published: bool
    user_feedback: Optional[str]
    edited_content: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReplySuggestionListResponse(BaseModel):
    """回复建议列表响应"""
    suggestions: List[ReplySuggestionResponse]
    total: int


class ReplyFeedbackRequest(BaseModel):
    """回复反馈请求"""
    suggestion_id: str = Field(..., description="建议 ID")
    feedback: FeedbackType = Field(..., description="反馈类型")
    edited_content: Optional[str] = Field(None, description="编辑后的内容")


class ReplyPublishRequest(BaseModel):
    """发布回复请求"""
    suggestion_id: str = Field(..., description="建议 ID")
    use_edited: bool = Field(True, description="使用编辑版本(如有)")


# ========== 标签管理 Schema ==========

class TagCreate(BaseModel):
    """创建标签请求"""
    name: str = Field(..., min_length=1, max_length=100, description="标签名称")
    display_name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    category: Optional[str] = Field(None, max_length=50, description="分类")
    description: Optional[str] = Field(None, description="描述")


class TagResponse(BaseModel):
    """标签响应"""
    id: str
    name: str
    display_name: str
    category: Optional[str]
    description: Optional[str]
    usage_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """标签列表响应"""
    tags: List[TagResponse]
    total: int


# ========== 统计 Schema ==========

class PlatformStatsResponse(BaseModel):
    """平台统计响应"""
    platform: str
    total_contents: int
    pending_count: int
    analyzed_count: int
    replied_count: int
    avg_quality_score: Optional[float]


class OverallStatsResponse(BaseModel):
    """总体统计响应"""
    total_contents: int
    total_platforms: int
    total_tags: int
    total_reply_suggestions: int
    contents_by_status: Dict[str, int]
    contents_by_type: Dict[str, int]
    platform_stats: List[PlatformStatsResponse]
