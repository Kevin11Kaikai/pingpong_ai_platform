"""
学习资源模块数据库模型
定义学习资源、学习路径、进度追踪的 ORM 模型
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Float,
    Boolean, Enum as SQLEnum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum

from app.shared.database import Base


class ResourceType(str, enum.Enum):
    """学习资源类型"""
    VIDEO = "video"           # 视频教程
    ARTICLE = "article"       # 文章/博客
    BOOK = "book"             # 书籍/电子书
    TUTORIAL = "tutorial"     # 互动教程
    EXERCISE = "exercise"     # 练习/训练方案
    COURSE = "course"         # 系统课程


class DifficultyLevel(str, enum.Enum):
    """难度等级"""
    BEGINNER = "beginner"           # 初学者
    INTERMEDIATE = "intermediate"   # 中级
    ADVANCED = "advanced"           # 高级
    PROFESSIONAL = "professional"   # 专业级


class ResourceCategory(str, enum.Enum):
    """资源分类"""
    TECHNIQUE = "technique"       # 技术动作（发球、接球、拉球等）
    TACTICS = "tactics"           # 战术打法
    RULES = "rules"               # 规则裁判
    EQUIPMENT = "equipment"       # 装备选购使用
    FITNESS = "fitness"           # 体能训练
    MENTAL = "mental"             # 心理训练
    COMPETITION = "competition"   # 比赛分析
    HISTORY = "history"           # 历史文化


class ResourceStatus(str, enum.Enum):
    """资源状态"""
    DRAFT = "draft"           # 草稿
    PUBLISHED = "published"   # 已发布
    ARCHIVED = "archived"     # 已归档


class LearningResource(Base):
    """学习资源模型"""
    __tablename__ = "learning_resources"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_type = Column(SQLEnum(ResourceType), nullable=False, index=True)
    category = Column(SQLEnum(ResourceCategory), nullable=False, index=True)
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=False, index=True)

    # 资源链接
    url = Column(String(1024), nullable=True)         # 外部链接
    thumbnail_url = Column(String(1024), nullable=True)  # 封面图

    # 元数据
    duration_minutes = Column(Integer, nullable=True)    # 时长（分钟，视频/课程）
    author = Column(String(255), nullable=True)          # 作者/讲师
    source = Column(String(255), nullable=True)          # 来源平台（YouTube, B站等）
    language = Column(String(20), default="zh", nullable=False)  # 语言

    # 标签与向量
    tags = Column(JSON, nullable=True)       # 标签列表 ["正手", "发球"]
    embedding = Column(JSON, nullable=True)  # 文本嵌入向量

    # 统计
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    # 状态
    is_featured = Column(Boolean, default=False)  # 推荐/精选
    status = Column(SQLEnum(ResourceStatus), default=ResourceStatus.PUBLISHED, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    path_items = relationship("LearningPathItem", back_populates="resource", cascade="all, delete-orphan")
    progress_records = relationship("UserProgress", back_populates="resource", cascade="all, delete-orphan")
    bookmarks = relationship("ResourceBookmark", back_populates="resource", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LearningResource(id={self.id}, title={self.title[:30]})>"


class LearningPath(Base):
    """学习路径（课程计划）模型"""
    __tablename__ = "learning_paths"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=False, index=True)
    category = Column(SQLEnum(ResourceCategory), nullable=True, index=True)  # 主要分类

    # 元数据
    estimated_hours = Column(Float, nullable=True)     # 预计完成时长（小时）
    target_audience = Column(Text, nullable=True)      # 适用人群描述
    learning_objectives = Column(JSON, nullable=True)  # 学习目标列表
    tags = Column(JSON, nullable=True)                 # 标签列表

    # 状态
    is_published = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    items = relationship(
        "LearningPathItem",
        back_populates="path",
        cascade="all, delete-orphan",
        order_by="LearningPathItem.order_index",
    )

    def __repr__(self) -> str:
        return f"<LearningPath(id={self.id}, title={self.title[:30]})>"


class LearningPathItem(Base):
    """学习路径资源条目模型（路径与资源的多对多中间表）"""
    __tablename__ = "learning_path_items"
    __table_args__ = (
        UniqueConstraint("path_id", "resource_id", name="uq_path_resource"),
    )

    id = Column(String(36), primary_key=True)
    path_id = Column(
        String(36),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_id = Column(
        String(36),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_index = Column(Integer, nullable=False, default=0)  # 路径中的排序
    notes = Column(Text, nullable=True)                       # 补充说明
    is_required = Column(Boolean, default=True)               # 是否必修

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    path = relationship("LearningPath", back_populates="items")
    resource = relationship("LearningResource", back_populates="path_items")

    def __repr__(self) -> str:
        return f"<LearningPathItem(path={self.path_id}, resource={self.resource_id}, order={self.order_index})>"


class UserProgress(Base):
    """用户学习进度模型"""
    __tablename__ = "user_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="uq_user_resource_progress"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)  # 用户标识（JWT sub 或匿名 ID）
    resource_id = Column(
        String(36),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 进度
    is_completed = Column(Boolean, default=False)
    progress_percent = Column(Float, default=0.0)   # 0.0 ~ 100.0
    last_accessed_at = Column(DateTime, nullable=True)

    # 反馈
    rating = Column(Integer, nullable=True)     # 1~5 星评分
    notes = Column(Text, nullable=True)         # 个人笔记

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    resource = relationship("LearningResource", back_populates="progress_records")

    def __repr__(self) -> str:
        return f"<UserProgress(user={self.user_id}, resource={self.resource_id}, pct={self.progress_percent})>"


class ResourceBookmark(Base):
    """资源收藏模型"""
    __tablename__ = "resource_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="uq_user_resource_bookmark"),
    )

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    resource_id = Column(
        String(36),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    resource = relationship("LearningResource", back_populates="bookmarks")

    def __repr__(self) -> str:
        return f"<ResourceBookmark(user={self.user_id}, resource={self.resource_id})>"


class TechniqueCategory(str, enum.Enum):
    """技术分类（用于知识图谱）"""
    SERVE = "serve"              # 发球
    RECEIVE = "receive"          # 接发球
    FOREHAND = "forehand"        # 正手技术
    BACKHAND = "backhand"        # 反手技术
    FOOTWORK = "footwork"        # 步法
    SPIN = "spin"                # 旋转
    STRATEGY = "strategy"        # 战术
    EQUIPMENT = "equipment"      # 装备知识
    RULES = "rules"              # 规则
    MENTAL = "mental"            # 心理素质
    PHYSICAL = "physical"        # 体能训练


class LearningStatus(str, enum.Enum):
    """学习状态"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    MASTERED = "mastered"        # 已掌握


class KnowledgePoint(Base):
    """知识点模型（知识图谱节点）"""
    __tablename__ = "knowledge_points"

    id = Column(String(36), primary_key=True)

    # 基本信息
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 分类
    category = Column(SQLEnum(TechniqueCategory), nullable=False, index=True)
    difficulty_level = Column(SQLEnum(DifficultyLevel), nullable=True)

    # 层级结构
    parent_id = Column(String(36), ForeignKey("knowledge_points.id"), nullable=True)
    level = Column(Integer, default=0)              # 层级深度
    sort_order = Column(Integer, default=0)

    # 详细内容
    definition = Column(Text, nullable=True)        # 定义
    key_points = Column(JSON, nullable=True)        # 要点列表
    common_mistakes = Column(JSON, nullable=True)   # 常见错误
    tips = Column(JSON, nullable=True)              # 技巧提示

    # 关联资源 ID 列表
    resource_ids = Column(JSON, nullable=True)

    # 向量嵌入
    embedding = Column(JSON, nullable=True)

    # 统计
    resource_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    parent = relationship("KnowledgePoint", remote_side=[id], backref="children")
    relations_from = relationship(
        "KnowledgeRelation",
        foreign_keys="KnowledgeRelation.from_point_id",
        back_populates="from_point",
        cascade="all, delete-orphan",
    )
    relations_to = relationship(
        "KnowledgeRelation",
        foreign_keys="KnowledgeRelation.to_point_id",
        back_populates="to_point",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KnowledgePoint(id={self.id}, name={self.name})>"


class KnowledgeRelation(Base):
    """知识点关系模型（知识图谱边）"""
    __tablename__ = "knowledge_relations"
    __table_args__ = (
        UniqueConstraint("from_point_id", "to_point_id", "relation_type", name="uq_knowledge_relation"),
    )

    id = Column(String(36), primary_key=True)
    from_point_id = Column(
        String(36),
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_point_id = Column(
        String(36),
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 关系类型: prerequisite(前置), related(相关), extends(扩展), similar(相似)
    relation_type = Column(String(50), nullable=False)
    weight = Column(Float, default=1.0)                 # 关系强度 0-1
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    from_point = relationship(
        "KnowledgePoint",
        foreign_keys=[from_point_id],
        back_populates="relations_from",
    )
    to_point = relationship(
        "KnowledgePoint",
        foreign_keys=[to_point_id],
        back_populates="relations_to",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeRelation(from={self.from_point_id}, to={self.to_point_id}, type={self.relation_type})>"


class UserLearningProfile(Base):
    """用户学习档案模型"""
    __tablename__ = "user_learning_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True)

    # 基本信息
    nickname = Column(String(100), nullable=True)
    current_level = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.BEGINNER)
    years_playing = Column(Integer, nullable=True)

    # 学习目标（JSON 数组）
    learning_goals = Column(JSON, nullable=True)    # ["提高发球", "学习正手弧圈"]
    weak_points = Column(JSON, nullable=True)       # ["反手", "步法"]
    interests = Column(JSON, nullable=True)         # ["进攻型打法", "旋转技术"]

    # 学习偏好
    preferred_resource_types = Column(JSON, nullable=True)  # ["video", "article"]
    preferred_duration_minutes = Column(Integer, default=30)
    daily_goal_minutes = Column(Integer, default=30)

    # 统计
    total_study_minutes = Column(Integer, default=0)
    total_resources_completed = Column(Integer, default=0)
    total_paths_completed = Column(Integer, default=0)
    current_streak_days = Column(Integer, default=0)
    longest_streak_days = Column(Integer, default=0)

    # 最后学习时间
    last_study_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    path_enrollments = relationship("UserPathEnrollment", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<UserLearningProfile(user_id={self.user_id})>"


class UserPathEnrollment(Base):
    """用户学习路径报名模型"""
    __tablename__ = "user_path_enrollments"
    __table_args__ = (
        UniqueConstraint("profile_id", "path_id", name="uq_user_path_enrollment"),
    )

    id = Column(String(36), primary_key=True)
    profile_id = Column(
        String(36),
        ForeignKey("user_learning_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path_id = Column(
        String(36),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 进度
    status = Column(SQLEnum(LearningStatus), default=LearningStatus.NOT_STARTED)
    progress_percent = Column(Float, default=0.0)
    current_item_index = Column(Integer, default=0)

    # 统计
    completed_items = Column(Integer, default=0)
    total_study_minutes = Column(Integer, default=0)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    profile = relationship("UserLearningProfile", back_populates="path_enrollments")
    path = relationship("LearningPath")

    def __repr__(self) -> str:
        return f"<UserPathEnrollment(profile={self.profile_id}, path={self.path_id})>"


class VideoAnalysisLink(Base):
    """视频分析关联模型（与 ball_tracking 集成）"""
    __tablename__ = "video_analysis_links"

    id = Column(String(36), primary_key=True)
    resource_id = Column(
        String(36),
        ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 关联的 ball_tracking 任务 ID
    ball_tracking_job_id = Column(String(36), nullable=False, index=True)

    # 分析片段信息
    start_time_seconds = Column(Float, default=0)
    end_time_seconds = Column(Float, nullable=True)

    # 分析类型: technique_demo(技术示范), common_mistake(常见错误), comparison(对比分析)
    analysis_type = Column(String(50), nullable=False)

    # 技术类型
    technique_category = Column(SQLEnum(TechniqueCategory), nullable=True)

    # 分析结果摘要（JSON）
    analysis_summary = Column(JSON, nullable=True)
    # {
    #   "technique": "forehand_loop",
    #   "key_findings": ["良好的髋部转动", "手臂延伸充分"],
    #   "speed_stats": {"avg": 25, "max": 32},
    #   "comparison_score": 0.85
    # }

    # AI 生成的技术解说
    ai_commentary = Column(Text, nullable=True)

    # 改进建议（JSON 数组）
    improvement_suggestions = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    resource = relationship("LearningResource")

    def __repr__(self) -> str:
        return f"<VideoAnalysisLink(resource={self.resource_id}, job={self.ball_tracking_job_id})>"
