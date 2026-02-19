"""
训练分析核心业务逻辑

导出所有服务的工厂函数。
"""

from app.training_analysis.core.session_service import (
    SessionService,
    get_session_service,
)
from app.training_analysis.core.metrics_service import (
    MetricsService,
    get_metrics_service,
)
from app.training_analysis.core.goal_service import (
    GoalService,
    get_goal_service,
)
from app.training_analysis.core.analysis_service import (
    AnalysisService,
    get_analysis_service,
)
from app.training_analysis.core.insight_service import (
    InsightService,
    get_insight_service,
)

__all__ = [
    # 会话服务
    "SessionService",
    "get_session_service",
    # 指标服务
    "MetricsService",
    "get_metrics_service",
    # 目标服务
    "GoalService",
    "get_goal_service",
    # 分析服务
    "AnalysisService",
    "get_analysis_service",
    # 洞察服务
    "InsightService",
    "get_insight_service",
]
