"""
学习资源模块 Pydantic Schema
定义所有 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ========== 枚举类型（Literal 轻量化用法） ==========

ResourceTypeEnum = Literal["video", "article", "book", "tutorial", "exercise", "course"]
DifficultyLevelEnum = Literal["beginner", "intermediate", "advanced", "professional"]
ResourceCategoryEnum = Literal[
    "technique", "tactics", "rules", "equipment",
    "fitness", "mental", "competition", "history"
]
ResourceStatusEnum = Literal["draft", "published", "archived"]


# ========== 学习资源 Schema ==========

class ResourceCreate(BaseModel):
    """创建学习资源请求"""
    title: str = Field(..., min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="详细描述")
    resource_type: ResourceTypeEnum = Field(..., description="资源类型")
    category: ResourceCategoryEnum = Field(..., description="资源分类")
    difficulty_level: DifficultyLevelEnum = Field(..., description="难度等级")
    url: Optional[str] = Field(None, max_length=1024, description="外部链接")
    thumbnail_url: Optional[str] = Field(None, max_length=1024, description="封面图 URL")
    duration_minutes: Optional[int] = Field(None, ge=1, description="时长（分钟）")
    author: Optional[str] = Field(None, max_length=255, description="作者/讲师")
    source: Optional[str] = Field(None, max_length=255, description="来源平台")
    language: str = Field("zh", max_length=20, description="语言代码")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_featured: bool = Field(False, description="是否推荐/精选")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """校验标签列表"""
        if v is not None:
            if len(v) > 20:
                raise ValueError("标签数量不能超过 20 个")
            v = [t.strip() for t in v if t.strip()]
        return v


class ResourceUpdate(BaseModel):
    """更新学习资源请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    resource_type: Optional[ResourceTypeEnum] = None
    category: Optional[ResourceCategoryEnum] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    url: Optional[str] = Field(None, max_length=1024)
    thumbnail_url: Optional[str] = Field(None, max_length=1024)
    duration_minutes: Optional[int] = Field(None, ge=1)
    author: Optional[str] = Field(None, max_length=255)
    source: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    status: Optional[ResourceStatusEnum] = None


class ResourceBrief(BaseModel):
    """资源摘要（用于列表）"""
    id: str
    title: str
    resource_type: str
    category: str
    difficulty_level: str
    duration_minutes: Optional[int]
    author: Optional[str]
    source: Optional[str]
    tags: Optional[List[str]]
    view_count: int
    like_count: int
    is_featured: bool
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceResponse(BaseModel):
    """资源详情响应"""
    id: str
    title: str
    description: Optional[str]
    resource_type: str
    category: str
    difficulty_level: str
    url: Optional[str]
    thumbnail_url: Optional[str]
    duration_minutes: Optional[int]
    author: Optional[str]
    source: Optional[str]
    language: str
    tags: Optional[List[str]]
    view_count: int
    like_count: int
    is_featured: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceListResponse(BaseModel):
    """资源列表响应"""
    resources: List[ResourceBrief]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========== 资源搜索 Schema ==========

class ResourceSearchRequest(BaseModel):
    """资源搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词（全文）")
    resource_type: Optional[ResourceTypeEnum] = Field(None, description="过滤类型")
    category: Optional[ResourceCategoryEnum] = Field(None, description="过滤分类")
    difficulty_level: Optional[DifficultyLevelEnum] = Field(None, description="过滤难度")
    status: ResourceStatusEnum = Field("published", description="资源状态")
    is_featured: Optional[bool] = Field(None, description="仅精选")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    sort_by: Literal["created_at", "view_count", "like_count", "duration_minutes"] = Field(
        "created_at", description="排序字段"
    )
    sort_order: Literal["asc", "desc"] = Field("desc", description="排序方向")


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询文本")
    top_k: int = Field(10, ge=1, le=50, description="返回结果数量")
    min_score: float = Field(0.3, ge=0.0, le=1.0, description="最低相似度阈值")
    category: Optional[ResourceCategoryEnum] = Field(None, description="限定分类")
    difficulty_level: Optional[DifficultyLevelEnum] = Field(None, description="限定难度")


class SemanticSearchResult(BaseModel):
    """语义搜索单条结果"""
    resource: ResourceBrief
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")


class SemanticSearchResponse(BaseModel):
    """语义搜索响应"""
    query: str
    results: List[SemanticSearchResult]
    total: int


# ========== 学习路径 Schema ==========

class LearningPathCreate(BaseModel):
    """创建学习路径请求"""
    title: str = Field(..., min_length=1, max_length=255, description="路径名称")
    description: Optional[str] = Field(None, description="路径描述")
    difficulty_level: DifficultyLevelEnum = Field(..., description="难度等级")
    category: Optional[ResourceCategoryEnum] = Field(None, description="主要分类")
    estimated_hours: Optional[float] = Field(None, ge=0.5, description="预计学习时长（小时）")
    target_audience: Optional[str] = Field(None, description="适用人群")
    learning_objectives: Optional[List[str]] = Field(None, description="学习目标")
    tags: Optional[List[str]] = Field(None, description="标签")
    is_published: bool = Field(True, description="是否发布")
    is_featured: bool = Field(False, description="是否精选")


class LearningPathUpdate(BaseModel):
    """更新学习路径请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    category: Optional[ResourceCategoryEnum] = None
    estimated_hours: Optional[float] = Field(None, ge=0.5)
    target_audience: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


class LearningPathItemCreate(BaseModel):
    """路径中添加资源请求"""
    resource_id: str = Field(..., description="资源 ID")
    order_index: int = Field(0, ge=0, description="在路径中的排序位置")
    notes: Optional[str] = Field(None, description="补充说明")
    is_required: bool = Field(True, description="是否必修项")


class LearningPathItemResponse(BaseModel):
    """路径条目响应"""
    id: str
    resource_id: str
    resource: ResourceBrief
    order_index: int
    notes: Optional[str]
    is_required: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningPathResponse(BaseModel):
    """学习路径详情响应"""
    id: str
    title: str
    description: Optional[str]
    difficulty_level: str
    category: Optional[str]
    estimated_hours: Optional[float]
    target_audience: Optional[str]
    learning_objectives: Optional[List[str]]
    tags: Optional[List[str]]
    is_published: bool
    is_featured: bool
    item_count: int
    created_at: datetime
    updated_at: datetime
    items: Optional[List[LearningPathItemResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class LearningPathBrief(BaseModel):
    """学习路径摘要（列表用）"""
    id: str
    title: str
    difficulty_level: str
    category: Optional[str]
    estimated_hours: Optional[float]
    tags: Optional[List[str]]
    is_published: bool
    is_featured: bool
    item_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningPathListResponse(BaseModel):
    """学习路径列表响应"""
    paths: List[LearningPathBrief]
    total: int


# ========== 用户进度 Schema ==========

class UserProgressCreate(BaseModel):
    """创建/更新进度请求"""
    resource_id: str = Field(..., description="资源 ID")
    user_id: str = Field(..., min_length=1, max_length=255, description="用户标识")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="完成百分比")
    is_completed: bool = Field(False, description="是否已完成")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分（1~5）")
    notes: Optional[str] = Field(None, description="个人笔记")


class UserProgressUpdate(BaseModel):
    """更新进度请求"""
    progress_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    is_completed: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None


class UserProgressResponse(BaseModel):
    """进度响应"""
    id: str
    user_id: str
    resource_id: str
    resource_title: str
    progress_percent: float
    is_completed: bool
    rating: Optional[int]
    notes: Optional[str]
    last_accessed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProgressSummary(BaseModel):
    """用户学习统计摘要"""
    user_id: str
    total_resources: int
    completed_resources: int
    in_progress_resources: int
    completion_rate: float      # 0.0 ~ 1.0
    total_hours_estimated: float
    average_rating: Optional[float]


class UserPathProgress(BaseModel):
    """用户在某学习路径的进度"""
    path_id: str
    path_title: str
    total_items: int
    completed_items: int
    completion_rate: float
    progress_details: List[UserProgressResponse]


# ========== 收藏 Schema ==========

class BookmarkCreate(BaseModel):
    """创建收藏请求"""
    user_id: str = Field(..., min_length=1, max_length=255, description="用户标识")
    resource_id: str = Field(..., description="资源 ID")


class BookmarkResponse(BaseModel):
    """收藏响应"""
    id: str
    user_id: str
    resource_id: str
    resource: ResourceBrief
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookmarkListResponse(BaseModel):
    """收藏列表响应"""
    bookmarks: List[BookmarkResponse]
    total: int


# ========== 统计 Schema ==========

class LearningStatsResponse(BaseModel):
    """学习资源统计响应"""
    total_resources: int
    resources_by_type: dict
    resources_by_category: dict
    resources_by_difficulty: dict
    total_paths: int
    featured_resources: int


# ========== 知识图谱 Schema ==========

TechniqueCategoryEnum = Literal[
    "serve", "receive", "forehand", "backhand", "footwork",
    "spin", "strategy", "equipment", "rules", "mental", "physical"
]
LearningStatusEnum = Literal["not_started", "in_progress", "completed", "mastered"]


class KnowledgePointCreate(BaseModel):
    """创建知识点请求"""
    name: str = Field(..., min_length=1, max_length=100, description="知识点标识（唯一）")
    display_name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    category: TechniqueCategoryEnum = Field(..., description="技术分类")
    difficulty_level: Optional[DifficultyLevelEnum] = Field(None, description="难度等级")
    parent_id: Optional[str] = Field(None, description="父节点 ID")
    sort_order: int = Field(0, ge=0, description="排序顺序")
    definition: Optional[str] = Field(None, description="定义")
    key_points: Optional[List[str]] = Field(None, description="要点列表")
    common_mistakes: Optional[List[str]] = Field(None, description="常见错误")
    tips: Optional[List[str]] = Field(None, description="技巧提示")
    resource_ids: Optional[List[str]] = Field(None, description="关联资源 ID")


class KnowledgePointUpdate(BaseModel):
    """更新知识点请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[TechniqueCategoryEnum] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    parent_id: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)
    definition: Optional[str] = None
    key_points: Optional[List[str]] = None
    common_mistakes: Optional[List[str]] = None
    tips: Optional[List[str]] = None
    resource_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


class KnowledgePointResponse(BaseModel):
    """知识点响应"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    category: str
    difficulty_level: Optional[str]
    parent_id: Optional[str]
    level: int
    sort_order: int
    definition: Optional[str]
    key_points: Optional[List[str]]
    common_mistakes: Optional[List[str]]
    tips: Optional[List[str]]
    resource_ids: Optional[List[str]]
    resource_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgePointBrief(BaseModel):
    """知识点简要信息"""
    id: str
    name: str
    display_name: str
    category: str
    difficulty_level: Optional[str]
    level: int
    resource_count: int

    model_config = ConfigDict(from_attributes=True)


class KnowledgePointTreeNode(BaseModel):
    """知识点树节点"""
    id: str
    name: str
    display_name: str
    category: str
    level: int
    resource_count: int
    children: List["KnowledgePointTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


class KnowledgeRelationCreate(BaseModel):
    """创建知识点关系请求"""
    from_point_id: str = Field(..., description="起始知识点 ID")
    to_point_id: str = Field(..., description="目标知识点 ID")
    relation_type: str = Field(..., description="关系类型: prerequisite, related, extends, similar")
    weight: float = Field(1.0, ge=0, le=1, description="关系强度")
    description: Optional[str] = Field(None, max_length=255, description="关系描述")


class KnowledgeRelationResponse(BaseModel):
    """知识点关系响应"""
    id: str
    from_point_id: str
    to_point_id: str
    relation_type: str
    weight: float
    description: Optional[str]
    from_point_name: Optional[str] = None
    to_point_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    nodes: List[KnowledgePointBrief]
    edges: List[KnowledgeRelationResponse]
    total_nodes: int
    total_edges: int


# ========== 用户学习档案 Schema ==========

class UserLearningProfileCreate(BaseModel):
    """创建用户学习档案请求"""
    user_id: str = Field(..., min_length=1, max_length=255, description="用户 ID")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    current_level: DifficultyLevelEnum = Field("beginner", description="当前水平")
    years_playing: Optional[int] = Field(None, ge=0, description="打球年限")
    learning_goals: Optional[List[str]] = Field(None, description="学习目标")
    weak_points: Optional[List[str]] = Field(None, description="薄弱点")
    interests: Optional[List[str]] = Field(None, description="兴趣方向")
    preferred_resource_types: Optional[List[ResourceTypeEnum]] = Field(None, description="偏好资源类型")
    preferred_duration_minutes: int = Field(30, ge=5, le=180, description="每次学习时长偏好")
    daily_goal_minutes: int = Field(30, ge=5, le=300, description="每日学习目标")


class UserLearningProfileUpdate(BaseModel):
    """更新用户学习档案请求"""
    nickname: Optional[str] = Field(None, max_length=100)
    current_level: Optional[DifficultyLevelEnum] = None
    years_playing: Optional[int] = Field(None, ge=0)
    learning_goals: Optional[List[str]] = None
    weak_points: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    preferred_resource_types: Optional[List[ResourceTypeEnum]] = None
    preferred_duration_minutes: Optional[int] = Field(None, ge=5, le=180)
    daily_goal_minutes: Optional[int] = Field(None, ge=5, le=300)


class UserLearningProfileResponse(BaseModel):
    """用户学习档案响应"""
    id: str
    user_id: str
    nickname: Optional[str]
    current_level: str
    years_playing: Optional[int]
    learning_goals: Optional[List[str]]
    weak_points: Optional[List[str]]
    interests: Optional[List[str]]
    preferred_resource_types: Optional[List[str]]
    preferred_duration_minutes: int
    daily_goal_minutes: int
    total_study_minutes: int
    total_resources_completed: int
    total_paths_completed: int
    current_streak_days: int
    longest_streak_days: int
    last_study_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPathEnrollmentResponse(BaseModel):
    """用户路径报名响应"""
    id: str
    profile_id: str
    path_id: str
    path_title: str
    status: str
    progress_percent: float
    current_item_index: int
    completed_items: int
    total_items: int
    total_study_minutes: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== 推荐 Schema ==========

class RecommendationRequest(BaseModel):
    """个性化推荐请求"""
    user_id: str = Field(..., description="用户 ID")
    recommendation_type: Literal["resources", "paths", "next_step"] = Field(
        "resources", description="推荐类型"
    )
    top_k: int = Field(5, ge=1, le=20, description="返回数量")
    exclude_completed: bool = Field(True, description="排除已完成")


class RecommendedResource(BaseModel):
    """推荐资源"""
    resource: ResourceBrief
    score: float = Field(..., ge=0, le=1, description="推荐分数")
    reasons: List[str] = Field(default_factory=list, description="推荐理由")


class RecommendedPath(BaseModel):
    """推荐路径"""
    path: LearningPathBrief
    score: float = Field(..., ge=0, le=1, description="推荐分数")
    reasons: List[str] = Field(default_factory=list, description="推荐理由")


class RecommendationResponse(BaseModel):
    """推荐响应"""
    user_id: str
    recommendation_type: str
    resources: Optional[List[RecommendedResource]] = None
    paths: Optional[List[RecommendedPath]] = None
    next_step: Optional[ResourceBrief] = None
    explanation: str = Field("", description="推荐说明")


class QuickRecommendationRequest(BaseModel):
    """快速推荐请求（无需用户档案）"""
    current_level: DifficultyLevelEnum = Field("beginner", description="当前水平")
    category: Optional[ResourceCategoryEnum] = Field(None, description="感兴趣分类")
    resource_type: Optional[ResourceTypeEnum] = Field(None, description="偏好资源类型")
    top_k: int = Field(5, ge=1, le=20, description="返回数量")


# ========== 视频分析集成 Schema ==========

class VideoAnalysisLinkCreate(BaseModel):
    """创建视频分析关联请求"""
    resource_id: str = Field(..., description="学习资源 ID")
    ball_tracking_job_id: str = Field(..., description="ball_tracking 任务 ID")
    start_time_seconds: float = Field(0, ge=0, description="开始时间（秒）")
    end_time_seconds: Optional[float] = Field(None, ge=0, description="结束时间（秒）")
    analysis_type: str = Field(..., description="分析类型: technique_demo, common_mistake, comparison")
    technique_category: Optional[TechniqueCategoryEnum] = Field(None, description="技术类型")


class VideoAnalysisLinkResponse(BaseModel):
    """视频分析关联响应"""
    id: str
    resource_id: str
    ball_tracking_job_id: str
    start_time_seconds: float
    end_time_seconds: Optional[float]
    analysis_type: str
    technique_category: Optional[str]
    analysis_summary: Optional[dict]
    ai_commentary: Optional[str]
    improvement_suggestions: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TechniqueAnalysisRequest(BaseModel):
    """技术动作分析请求"""
    resource_id: str = Field(..., description="学习资源 ID")
    ball_tracking_job_id: str = Field(..., description="ball_tracking 任务 ID")
    technique_category: TechniqueCategoryEnum = Field(..., description="技术类型")
    generate_commentary: bool = Field(True, description="是否生成 AI 解说")


class TechniqueAnalysisResponse(BaseModel):
    """技术动作分析响应"""
    link_id: str
    resource_id: str
    ball_tracking_job_id: str
    technique_category: str
    analysis_summary: dict
    ai_commentary: Optional[str]
    improvement_suggestions: List[str]
    comparison_score: Optional[float] = Field(None, ge=0, le=1, description="与标准动作对比分数")


# ========== 用户学习统计 Schema ==========

class UserLearningStatsResponse(BaseModel):
    """用户学习统计响应"""
    user_id: str
    total_study_minutes: int
    total_resources_completed: int
    total_paths_completed: int
    current_streak_days: int
    longest_streak_days: int
    resources_by_type: dict
    resources_by_category: dict
    recent_activity: List[dict]  # 最近学习记录
    daily_stats: List[dict]      # 每日学习统计（最近30天）
