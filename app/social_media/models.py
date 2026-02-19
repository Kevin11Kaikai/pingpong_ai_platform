"""
社交媒体问答模块数据库模型
定义平台配置、抓取任务、内容、标签、回复建议的 ORM 模型
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Float,
    Boolean, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.shared.database import Base


class Platform(str, enum.Enum):
    """社交媒体平台类型"""
    ZHIHU = "zhihu"           # 知乎
    WEIBO = "weibo"           # 微博
    TIEBA = "tieba"           # 贴吧
    DOUYIN = "douyin"         # 抖音评论区
    XIAOHONGSHU = "xiaohongshu"  # 小红书
    BILIBILI = "bilibili"     # B站评论区
    REDDIT = "reddit"         # Reddit
    CUSTOM = "custom"         # 自定义来源


class ContentType(str, enum.Enum):
    """内容类型"""
    QUESTION = "question"     # 问题/提问
    ANSWER = "answer"         # 回答
    POST = "post"             # 帖子/文章
    COMMENT = "comment"       # 评论
    THREAD = "thread"         # 讨论串


class ContentStatus(str, enum.Enum):
    """内容状态"""
    PENDING = "pending"       # 待处理
    ANALYZED = "analyzed"     # 已分析
    REPLIED = "replied"       # 已生成回复
    PUBLISHED = "published"   # 已发布
    ARCHIVED = "archived"     # 已归档


class SocialPlatformConfig(Base):
    """社交平台配置模型"""
    __tablename__ = "social_platform_configs"

    id = Column(String(36), primary_key=True)
    platform = Column(SQLEnum(Platform), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)  # 平台显示名
    base_url = Column(String(512), nullable=True)       # 平台基础 URL

    # 抓取配置
    scrape_enabled = Column(Boolean, default=True)
    scrape_interval_minutes = Column(Integer, default=60)  # 抓取间隔
    scrape_keywords = Column(JSON, nullable=True)  # 关键词列表 ["乒乓球", "发球技术"]
    scrape_max_items = Column(Integer, default=100)  # 单次最大抓取数

    # 认证配置（加密存储）
    auth_config = Column(JSON, nullable=True)  # {"cookie": "...", "token": "..."}

    # 速率限制
    rate_limit_per_minute = Column(Integer, default=10)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    contents = relationship("SocialContent", back_populates="platform_config")
    scrape_tasks = relationship("ScrapeTask", back_populates="platform_config")

    def __repr__(self) -> str:
        return f"<SocialPlatformConfig(platform={self.platform})>"


class ScrapeTask(Base):
    """抓取任务模型"""
    __tablename__ = "scrape_tasks"

    id = Column(String(36), primary_key=True)
    platform_config_id = Column(
        String(36),
        ForeignKey("social_platform_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 任务配置
    keywords = Column(JSON, nullable=True)  # 本次任务的关键词
    target_url = Column(String(1024), nullable=True)  # 指定抓取的 URL

    # 任务状态
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 结果统计
    items_found = Column(Integer, default=0)
    items_saved = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    platform_config = relationship("SocialPlatformConfig", back_populates="scrape_tasks")

    def __repr__(self) -> str:
        return f"<ScrapeTask(id={self.id}, status={self.status})>"


class SocialContent(Base):
    """社交媒体内容模型"""
    __tablename__ = "social_contents"

    id = Column(String(36), primary_key=True)
    platform_config_id = Column(
        String(36),
        ForeignKey("social_platform_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 原始内容标识
    external_id = Column(String(255), nullable=True, index=True)  # 平台上的原始 ID
    external_url = Column(String(1024), nullable=True)  # 原始链接

    # 内容信息
    content_type = Column(SQLEnum(ContentType), nullable=False)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=True)
    author_id = Column(String(255), nullable=True)

    # 父级内容（用于回答关联问题、评论关联帖子）
    parent_id = Column(String(36), ForeignKey("social_contents.id"), nullable=True)

    # 互动数据
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    # 发布时间（原始平台上的发布时间）
    published_at = Column(DateTime, nullable=True)

    # 内容标签
    tags = Column(JSON, nullable=True)  # ["技术", "发球", "初学者"]

    # 处理状态
    status = Column(SQLEnum(ContentStatus), default=ContentStatus.PENDING)

    # 内容质量评分（AI 分析后填充）
    quality_score = Column(Float, nullable=True)  # 0-1 质量分
    relevance_score = Column(Float, nullable=True)  # 0-1 相关度

    # 向量嵌入（用于语义搜索）
    embedding = Column(JSON, nullable=True)  # 存储为 list

    # 分析结果
    analysis_result = Column(JSON, nullable=True)
    # {
    #   "topics": ["发球", "旋转"],
    #   "question_type": "technique",
    #   "difficulty_level": "beginner",
    #   "sentiment": "neutral",
    #   "key_points": ["..."]
    # }

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    platform_config = relationship("SocialPlatformConfig", back_populates="contents")
    parent = relationship("SocialContent", remote_side=[id], backref="children")
    reply_suggestions = relationship(
        "ReplySuggestion",
        back_populates="content",
        cascade="all, delete-orphan",
    )
    content_tags = relationship(
        "ContentTagMapping",
        back_populates="content",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SocialContent(id={self.id}, type={self.content_type})>"


class ContentTag(Base):
    """内容标签模型"""
    __tablename__ = "content_tags"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)  # 显示名称
    category = Column(String(50), nullable=True)  # 标签分类: technique, equipment, rule, etc.
    description = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)

    # 向量嵌入（用于标签相似度计算）
    embedding = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    content_mappings = relationship("ContentTagMapping", back_populates="tag")

    def __repr__(self) -> str:
        return f"<ContentTag(name={self.name})>"


class ContentTagMapping(Base):
    """内容-标签关联模型"""
    __tablename__ = "content_tag_mappings"

    id = Column(String(36), primary_key=True)
    content_id = Column(
        String(36),
        ForeignKey("social_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id = Column(
        String(36),
        ForeignKey("content_tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confidence = Column(Float, default=1.0)  # 标签置信度
    source = Column(String(50), default="manual")  # manual, auto, ai

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    content = relationship("SocialContent", back_populates="content_tags")
    tag = relationship("ContentTag", back_populates="content_mappings")


class ReplySuggestion(Base):
    """回复建议模型"""
    __tablename__ = "reply_suggestions"

    id = Column(String(36), primary_key=True)
    content_id = Column(
        String(36),
        ForeignKey("social_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 回复内容
    reply_content = Column(Text, nullable=False)

    # 生成参数
    model_used = Column(String(50), default="gpt-4o-mini")
    temperature = Column(Float, default=0.7)
    style = Column(String(50), default="professional")  # professional, friendly, concise

    # RAG 引用
    sources = Column(JSON, nullable=True)  # 引用的文档来源

    # 评分和状态
    quality_score = Column(Float, nullable=True)  # AI 自评分数
    is_selected = Column(Boolean, default=False)  # 是否被选中使用
    is_published = Column(Boolean, default=False)  # 是否已发布

    # 用户反馈
    user_feedback = Column(String(20), nullable=True)  # helpful, not_helpful, edited
    edited_content = Column(Text, nullable=True)  # 用户编辑后的版本

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    content = relationship("SocialContent", back_populates="reply_suggestions")

    def __repr__(self) -> str:
        return f"<ReplySuggestion(id={self.id}, content_id={self.content_id})>"
