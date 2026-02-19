"""
装备推荐模块 Pydantic Schema
定义所有 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ========== 枚举类型 ==========

PlayingStyleType = Literal["offensive", "defensive", "all_round", "chopper"]
GripStyleType = Literal["shakehand", "penhold_chinese", "penhold_japanese"]
SkillLevelType = Literal["beginner", "intermediate", "advanced", "professional"]


# ========== 品牌 Schema ==========

class BrandCreate(BaseModel):
    """创建品牌请求"""
    name: str = Field(..., min_length=1, max_length=100, description="品牌名称")
    display_name: Optional[str] = Field(None, max_length=100, description="品牌中文名")
    country: Optional[str] = Field(None, max_length=50, description="国家/地区")
    description: Optional[str] = Field(None, description="品牌描述")
    logo_url: Optional[str] = Field(None, max_length=512, description="Logo URL")
    website_url: Optional[str] = Field(None, max_length=512, description="官网 URL")


class BrandUpdate(BaseModel):
    """更新品牌请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=512)
    website_url: Optional[str] = Field(None, max_length=512)
    is_active: Optional[bool] = None


class BrandResponse(BaseModel):
    """品牌响应"""
    id: str
    name: str
    display_name: Optional[str]
    country: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    website_url: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrandListResponse(BaseModel):
    """品牌列表响应"""
    brands: List[BrandResponse]
    total: int


# ========== 分类 Schema ==========

class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., min_length=1, max_length=50, description="分类标识")
    display_name: str = Field(..., min_length=1, max_length=100, description="分类显示名")
    description: Optional[str] = None
    parent_id: Optional[str] = Field(None, description="父分类ID")
    sort_order: int = Field(0, ge=0, description="排序顺序")


class CategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None
    sort_order: Optional[int] = Field(None, ge=0)


class CategoryResponse(BaseModel):
    """分类响应"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    parent_id: Optional[str]
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeResponse(BaseModel):
    """分类树响应"""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    sort_order: int
    subcategories: List["CategoryTreeResponse"] = []

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    """分类列表响应"""
    categories: List[CategoryResponse]
    total: int


# ========== 装备 Schema ==========

class EquipmentCreate(BaseModel):
    """创建装备请求"""
    name: str = Field(..., min_length=1, max_length=255, description="装备名称")
    brand_id: str = Field(..., description="品牌ID")
    category_id: str = Field(..., description="分类ID")
    model_number: Optional[str] = Field(None, max_length=100, description="型号")
    description: Optional[str] = Field(None, description="装备描述")

    # 价格
    price_min: Optional[float] = Field(None, ge=0, description="最低价格")
    price_max: Optional[float] = Field(None, ge=0, description="最高价格")
    price_currency: str = Field("CNY", max_length=10, description="货币单位")

    # 性能评分
    speed_rating: Optional[int] = Field(None, ge=0, le=100, description="速度评分")
    spin_rating: Optional[int] = Field(None, ge=0, le=100, description="旋转评分")
    control_rating: Optional[int] = Field(None, ge=0, le=100, description="控制评分")

    # 适用人群
    suitable_styles: Optional[List[PlayingStyleType]] = Field(None, description="适合打法")
    suitable_levels: Optional[List[SkillLevelType]] = Field(None, description="适合水平")
    suitable_grips: Optional[List[GripStyleType]] = Field(None, description="适合握法")

    # 规格和图片
    specifications: Optional[Dict[str, Any]] = Field(None, description="详细规格")
    image_urls: Optional[List[str]] = Field(None, description="图片URL列表")

    is_featured: bool = Field(False, description="是否精选")


class EquipmentUpdate(BaseModel):
    """更新装备请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    brand_id: Optional[str] = None
    category_id: Optional[str] = None
    model_number: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None

    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    price_currency: Optional[str] = Field(None, max_length=10)

    speed_rating: Optional[int] = Field(None, ge=0, le=100)
    spin_rating: Optional[int] = Field(None, ge=0, le=100)
    control_rating: Optional[int] = Field(None, ge=0, le=100)

    suitable_styles: Optional[List[PlayingStyleType]] = None
    suitable_levels: Optional[List[SkillLevelType]] = None
    suitable_grips: Optional[List[GripStyleType]] = None

    specifications: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = None

    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class EquipmentBrief(BaseModel):
    """装备简要信息"""
    id: str
    name: str
    brand_name: str
    category_name: str
    price_min: Optional[float]
    price_max: Optional[float]
    speed_rating: Optional[int]
    spin_rating: Optional[int]
    control_rating: Optional[int]
    avg_rating: float
    review_count: int
    image_url: Optional[str]  # 首图

    model_config = ConfigDict(from_attributes=True)


class EquipmentResponse(BaseModel):
    """装备详情响应"""
    id: str
    name: str
    brand_id: str
    brand_name: str
    category_id: str
    category_name: str
    model_number: Optional[str]
    description: Optional[str]

    price_min: Optional[float]
    price_max: Optional[float]
    price_currency: str

    speed_rating: Optional[int]
    spin_rating: Optional[int]
    control_rating: Optional[int]

    suitable_styles: Optional[List[str]]
    suitable_levels: Optional[List[str]]
    suitable_grips: Optional[List[str]]

    specifications: Optional[Dict[str, Any]]
    image_urls: Optional[List[str]]

    view_count: int
    review_count: int
    avg_rating: float

    is_active: bool
    is_featured: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EquipmentListResponse(BaseModel):
    """装备列表响应"""
    equipment: List[EquipmentBrief]
    total: int
    page: int
    page_size: int


class EquipmentSearchRequest(BaseModel):
    """装备搜索请求"""
    query: Optional[str] = Field(None, max_length=200, description="搜索关键词")
    category_id: Optional[str] = Field(None, description="分类ID")
    brand_ids: Optional[List[str]] = Field(None, description="品牌ID列表")
    price_min: Optional[float] = Field(None, ge=0, description="最低价格")
    price_max: Optional[float] = Field(None, ge=0, description="最高价格")
    min_speed: Optional[int] = Field(None, ge=0, le=100, description="最低速度评分")
    min_spin: Optional[int] = Field(None, ge=0, le=100, description="最低旋转评分")
    min_control: Optional[int] = Field(None, ge=0, le=100, description="最低控制评分")
    suitable_styles: Optional[List[PlayingStyleType]] = None
    suitable_levels: Optional[List[SkillLevelType]] = None
    is_featured: Optional[bool] = None
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class EquipmentCompareRequest(BaseModel):
    """装备对比请求"""
    equipment_ids: List[str] = Field(..., min_length=2, max_length=5, description="装备ID列表")


class EquipmentCompareResponse(BaseModel):
    """装备对比响应"""
    equipment: List[EquipmentResponse]
    comparison_summary: Dict[str, Any]  # 对比摘要


# ========== 用户偏好档案 Schema ==========

class UserProfileCreate(BaseModel):
    """创建用户偏好档案请求"""
    user_id: str = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, max_length=100, description="昵称")
    years_playing: Optional[int] = Field(None, ge=0, le=50, description="打球年限")

    playing_style: Optional[PlayingStyleType] = Field(None, description="打法风格")
    grip_style: Optional[GripStyleType] = Field(None, description="握拍方式")
    skill_level: Optional[SkillLevelType] = Field(None, description="技术水平")

    prefer_speed: int = Field(50, ge=0, le=100, description="速度偏好")
    prefer_spin: int = Field(50, ge=0, le=100, description="旋转偏好")
    prefer_control: int = Field(50, ge=0, le=100, description="控制偏好")

    budget_min: Optional[float] = Field(None, ge=0, description="预算下限")
    budget_max: Optional[float] = Field(None, ge=0, description="预算上限")
    budget_currency: str = Field("CNY", max_length=10, description="货币单位")

    current_equipment: Optional[Dict[str, str]] = Field(None, description="当前装备")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="补充信息")


class UserProfileUpdate(BaseModel):
    """更新用户偏好档案请求"""
    nickname: Optional[str] = Field(None, max_length=100)
    years_playing: Optional[int] = Field(None, ge=0, le=50)

    playing_style: Optional[PlayingStyleType] = None
    grip_style: Optional[GripStyleType] = None
    skill_level: Optional[SkillLevelType] = None

    prefer_speed: Optional[int] = Field(None, ge=0, le=100)
    prefer_spin: Optional[int] = Field(None, ge=0, le=100)
    prefer_control: Optional[int] = Field(None, ge=0, le=100)

    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    budget_currency: Optional[str] = Field(None, max_length=10)

    current_equipment: Optional[Dict[str, str]] = None
    additional_info: Optional[Dict[str, Any]] = None


class UserProfileResponse(BaseModel):
    """用户偏好档案响应"""
    id: str
    user_id: str
    nickname: Optional[str]
    years_playing: Optional[int]

    playing_style: Optional[str]
    grip_style: Optional[str]
    skill_level: Optional[str]

    prefer_speed: int
    prefer_spin: int
    prefer_control: int

    budget_min: Optional[float]
    budget_max: Optional[float]
    budget_currency: str

    current_equipment: Optional[Dict[str, str]]
    additional_info: Optional[Dict[str, Any]]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== 评价 Schema ==========

class ReviewCreate(BaseModel):
    """创建评价请求"""
    equipment_id: str = Field(..., description="装备ID")
    overall_rating: int = Field(..., ge=1, le=5, description="总体评分")
    speed_rating: Optional[int] = Field(None, ge=1, le=5, description="速度评分")
    spin_rating: Optional[int] = Field(None, ge=1, le=5, description="旋转评分")
    control_rating: Optional[int] = Field(None, ge=1, le=5, description="控制评分")
    durability_rating: Optional[int] = Field(None, ge=1, le=5, description="耐用性评分")
    value_rating: Optional[int] = Field(None, ge=1, le=5, description="性价比评分")

    title: Optional[str] = Field(None, max_length=255, description="评价标题")
    content: Optional[str] = Field(None, description="评价内容")
    pros: Optional[List[str]] = Field(None, description="优点")
    cons: Optional[List[str]] = Field(None, description="缺点")
    usage_duration: Optional[str] = Field(None, max_length=50, description="使用时长")


class ReviewUpdate(BaseModel):
    """更新评价请求"""
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    speed_rating: Optional[int] = Field(None, ge=1, le=5)
    spin_rating: Optional[int] = Field(None, ge=1, le=5)
    control_rating: Optional[int] = Field(None, ge=1, le=5)
    durability_rating: Optional[int] = Field(None, ge=1, le=5)
    value_rating: Optional[int] = Field(None, ge=1, le=5)

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    usage_duration: Optional[str] = Field(None, max_length=50)


class ReviewResponse(BaseModel):
    """评价响应"""
    id: str
    equipment_id: str
    equipment_name: str
    user_profile_id: Optional[str]
    user_nickname: Optional[str]

    overall_rating: int
    speed_rating: Optional[int]
    spin_rating: Optional[int]
    control_rating: Optional[int]
    durability_rating: Optional[int]
    value_rating: Optional[int]

    title: Optional[str]
    content: Optional[str]
    pros: Optional[List[str]]
    cons: Optional[List[str]]
    usage_duration: Optional[str]

    helpful_count: int
    is_verified: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """评价列表响应"""
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int


# ========== 推荐 Schema ==========

class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: str = Field(..., description="用户ID")
    recommendation_type: str = Field(
        "full_setup",
        description="推荐类型: blade, rubber, full_setup"
    )
    top_k: int = Field(5, ge=1, le=20, description="返回数量")

    # 可选的临时覆盖参数
    override_style: Optional[PlayingStyleType] = None
    override_level: Optional[SkillLevelType] = None
    override_budget_max: Optional[float] = None


class RecommendedItem(BaseModel):
    """推荐项"""
    equipment: EquipmentBrief
    score: float = Field(..., ge=0, le=1, description="匹配分数")
    reasons: List[str] = Field(..., description="推荐理由")


class RecommendationResponse(BaseModel):
    """推荐响应"""
    id: str
    user_profile_id: str
    recommendation_type: str
    recommended_items: List[RecommendedItem]
    explanation: Optional[str]
    created_at: datetime


class SimilarEquipmentRequest(BaseModel):
    """相似装备请求"""
    equipment_id: str = Field(..., description="参考装备ID")
    top_k: int = Field(5, ge=1, le=20, description="返回数量")


class SimilarEquipmentResponse(BaseModel):
    """相似装备响应"""
    reference_equipment: EquipmentBrief
    similar_equipment: List[EquipmentBrief]
    similarity_scores: List[float]
