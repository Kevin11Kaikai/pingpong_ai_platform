"""
社交媒体问答模块

提供社交媒体内容抓取、分析和回复生成功能
"""

from app.social_media.models import (
    Platform,
    ContentType,
    ContentStatus,
    SocialPlatformConfig,
    ScrapeTask,
    SocialContent,
    ContentTag,
    ContentTagMapping,
    ReplySuggestion,
)

from app.social_media.core import (
    ContentService,
    get_content_service,
    AnalysisService,
    get_analysis_service,
    ReplyService,
    get_reply_service,
    ScraperService,
    get_scraper_service,
)

__all__ = [
    # 枚举
    "Platform",
    "ContentType",
    "ContentStatus",
    # 模型
    "SocialPlatformConfig",
    "ScrapeTask",
    "SocialContent",
    "ContentTag",
    "ContentTagMapping",
    "ReplySuggestion",
    # 服务
    "ContentService",
    "get_content_service",
    "AnalysisService",
    "get_analysis_service",
    "ReplyService",
    "get_reply_service",
    "ScraperService",
    "get_scraper_service",
]
