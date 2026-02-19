"""
装备推荐模块数据库模型
定义装备、品牌、分类、用户偏好和评价的 ORM 模型
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Float,
    Boolean, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.shared.database import Base


class PlayingStyle(str, enum.Enum):
    """打法风格"""
    OFFENSIVE = "offensive"  # 进攻型
    DEFENSIVE = "defensive"  # 防守型
    ALL_ROUND = "all_round"  # 全面型
    CHOPPER = "chopper"  # 削球型


class GripStyle(str, enum.Enum):
    """握拍方式"""
    SHAKEHAND = "shakehand"  # 横拍
    PENHOLD_CHINESE = "penhold_chinese"  # 中式直拍
    PENHOLD_JAPANESE = "penhold_japanese"  # 日式直拍


class SkillLevel(str, enum.Enum):
    """技术水平"""
    BEGINNER = "beginner"  # 初学者
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    PROFESSIONAL = "professional"  # 专业


class EquipmentCategory(Base):
    """装备分类模型"""
    __tablename__ = "equipment_categories"

    id = Column(String(36), primary_key=True)
    name = Column(String(50), nullable=False, unique=True)  # blade, rubber, ball, etc.
    display_name = Column(String(100), nullable=False)  # 底板, 胶皮, 球
    description = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey("equipment_categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    parent = relationship("EquipmentCategory", remote_side=[id], backref="subcategories")
    equipment = relationship("Equipment", back_populates="category")

    def __repr__(self) -> str:
        return f"<EquipmentCategory(id={self.id}, name={self.name})>"


class Brand(Base):
    """品牌模型"""
    __tablename__ = "brands"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=True)  # 中文名称
    country = Column(String(50), nullable=True)  # 国家/地区
    description = Column(Text, nullable=True)
    logo_url = Column(String(512), nullable=True)
    website_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    equipment = relationship("Equipment", back_populates="brand")

    def __repr__(self) -> str:
        return f"<Brand(id={self.id}, name={self.name})>"


class Equipment(Base):
    """装备产品模型"""
    __tablename__ = "equipment"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    brand_id = Column(
        String(36),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        String(36),
        ForeignKey("equipment_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 基本信息
    model_number = Column(String(100), nullable=True)  # 型号
    description = Column(Text, nullable=True)

    # 价格信息
    price_min = Column(Float, nullable=True)  # 最低价格
    price_max = Column(Float, nullable=True)  # 最高价格
    price_currency = Column(String(10), default="CNY")

    # 性能参数 (0-100 评分)
    speed_rating = Column(Integer, nullable=True)  # 速度
    spin_rating = Column(Integer, nullable=True)  # 旋转
    control_rating = Column(Integer, nullable=True)  # 控制

    # 适用人群 (JSON 数组)
    suitable_styles = Column(JSON, nullable=True)  # ["offensive", "all_round"]
    suitable_levels = Column(JSON, nullable=True)  # ["intermediate", "advanced"]
    suitable_grips = Column(JSON, nullable=True)  # ["shakehand", "penhold_chinese"]

    # 详细规格 (JSON，根据分类不同内容不同)
    specifications = Column(JSON, nullable=True)
    # 底板: layers(层数), weight(重量), thickness(厚度), composition(材质)
    # 胶皮: hardness(硬度), thickness(厚度), surface(表面), sponge(海绵)

    # 图片
    image_urls = Column(JSON, nullable=True)  # ["url1", "url2"]

    # 向量嵌入 (用于相似度搜索)
    embedding = Column(JSON, nullable=True)  # 存储为 list

    # 统计信息
    view_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)

    # 状态
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # 推荐/精选

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    brand = relationship("Brand", back_populates="equipment")
    category = relationship("EquipmentCategory", back_populates="equipment")
    reviews = relationship(
        "EquipmentReview",
        back_populates="equipment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Equipment(id={self.id}, name={self.name})>"


class UserEquipmentProfile(Base):
    """用户装备偏好档案"""
    __tablename__ = "user_equipment_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, unique=True, index=True)

    # 基本信息
    nickname = Column(String(100), nullable=True)
    years_playing = Column(Integer, nullable=True)  # 打球年限

    # 打法风格
    playing_style = Column(SQLEnum(PlayingStyle), nullable=True)
    grip_style = Column(SQLEnum(GripStyle), nullable=True)
    skill_level = Column(SQLEnum(SkillLevel), nullable=True)

    # 偏好设置 (0-100)
    prefer_speed = Column(Integer, default=50)  # 速度偏好
    prefer_spin = Column(Integer, default=50)  # 旋转偏好
    prefer_control = Column(Integer, default=50)  # 控制偏好

    # 预算范围
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    budget_currency = Column(String(10), default="CNY")

    # 当前使用的装备 (JSON)
    current_equipment = Column(JSON, nullable=True)
    # {"blade": "equipment_id", "forehand_rubber": "id", "backhand_rubber": "id"}

    # 补充信息 (JSON)
    additional_info = Column(JSON, nullable=True)
    # {"hand": "right", "weak_points": ["backhand"], "goals": ["improve spin"]}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    reviews = relationship("EquipmentReview", back_populates="user_profile")
    recommendations = relationship("EquipmentRecommendation", back_populates="user_profile")

    def __repr__(self) -> str:
        return f"<UserEquipmentProfile(id={self.id}, user_id={self.user_id})>"


class EquipmentReview(Base):
    """装备评价模型"""
    __tablename__ = "equipment_reviews"

    id = Column(String(36), primary_key=True)
    equipment_id = Column(
        String(36),
        ForeignKey("equipment.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_profile_id = Column(
        String(36),
        ForeignKey("user_equipment_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 评分 (1-5)
    overall_rating = Column(Integer, nullable=False)
    speed_rating = Column(Integer, nullable=True)
    spin_rating = Column(Integer, nullable=True)
    control_rating = Column(Integer, nullable=True)
    durability_rating = Column(Integer, nullable=True)
    value_rating = Column(Integer, nullable=True)  # 性价比

    # 评价内容
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    pros = Column(JSON, nullable=True)  # ["优点1", "优点2"]
    cons = Column(JSON, nullable=True)  # ["缺点1", "缺点2"]

    # 使用情况
    usage_duration = Column(String(50), nullable=True)  # "1-3 months", "6-12 months"

    # 互动
    helpful_count = Column(Integer, default=0)

    # 状态
    is_verified = Column(Boolean, default=False)  # 已验证购买
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    equipment = relationship("Equipment", back_populates="reviews")
    user_profile = relationship("UserEquipmentProfile", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<EquipmentReview(id={self.id}, rating={self.overall_rating})>"


class EquipmentRecommendation(Base):
    """装备推荐记录"""
    __tablename__ = "equipment_recommendations"

    id = Column(String(36), primary_key=True)
    user_profile_id = Column(
        String(36),
        ForeignKey("user_equipment_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 推荐类型
    recommendation_type = Column(String(50), nullable=False)  # blade, rubber, full_setup

    # 推荐结果 (JSON)
    recommended_items = Column(JSON, nullable=False)
    # [{"equipment_id": "...", "score": 0.95, "reasons": ["适合进攻型打法"]}]

    # 推荐理由
    explanation = Column(Text, nullable=True)

    # 用户反馈
    user_feedback = Column(String(20), nullable=True)  # helpful, not_helpful, purchased

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user_profile = relationship("UserEquipmentProfile", back_populates="recommendations")

    def __repr__(self) -> str:
        return f"<EquipmentRecommendation(id={self.id}, type={self.recommendation_type})>"
