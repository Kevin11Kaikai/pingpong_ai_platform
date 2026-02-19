from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置，从 .env 文件读取
    所有敏感配置通过环境变量注入，禁止硬编码
    """

    # LLM API（兼容任何 OpenAI 格式的 API：OpenAI 官方、OhMyGPT、其他代理）
    # 只需修改 base_url 和 key 即可切换服务商
    llm_api_key: str
    llm_base_url: str = "https://api.ohmygpt.com/v1"

    # App
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/pingpong.db"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Ball Tracking Configuration
    ball_tracking_upload_dir: str = "./data/uploads/videos"
    ball_tracking_output_dir: str = "./data/outputs/ball_tracking"
    ball_tracking_max_file_size_mb: int = 500

    # BlurBall Model Paths
    blurball_config_name: str = "inference_blurball"
    blurball_checkpoint_path: str = "./external/blurball/checkpoints/blurball_best"

    # Ball Tracking Processing
    ball_tracking_batch_size: int = 16
    ball_tracking_detection_threshold: float = 0.5
    ball_tracking_max_gap_frames: int = 5

    # Equipment Recommendation Configuration
    equipment_image_dir: str = "./data/uploads/equipment"
    equipment_default_page_size: int = 20
    equipment_max_compare_items: int = 5
    equipment_recommendation_top_k: int = 5

    # Social Media Configuration
    social_media_scrape_enabled: bool = True
    social_media_default_interval_minutes: int = 60
    social_media_max_items_per_scrape: int = 100
    social_media_analysis_batch_size: int = 50
    social_media_reply_max_length: int = 500
    social_media_reply_default_style: str = "professional"

    # Learning Resources Configuration
    learning_resources_default_page_size: int = 20
    learning_resources_search_top_k: int = 10
    learning_resources_search_min_score: float = 0.3
    learning_resources_featured_count: int = 6

    # Learning Resources - User Profile & Recommendation
    learning_resource_upload_dir: str = "./data/uploads/learning"
    learning_path_recommendation_top_k: int = 5
    learning_daily_study_goal_minutes: int = 30
    learning_streak_reset_hours: int = 48  # 超过48小时未学习重置连续天数

    # Learning Resources - Video Analysis Integration
    learning_video_analysis_enabled: bool = True
    learning_ai_commentary_model: str = "gpt-4o-mini"
    learning_ai_commentary_temperature: float = 0.7

    # Training Analysis Configuration
    training_analysis_default_page_size: int = 20
    training_analysis_max_sessions_per_query: int = 100
    training_analysis_snapshot_retention_days: int = 365
    training_analysis_insight_retention_days: int = 90

    # Training Analysis - AI Insight Generation
    training_insight_model: str = "gpt-4o-mini"
    training_insight_temperature: float = 0.7
    training_insight_max_tokens: int = 1000

    # Training Analysis - Metrics Calculation
    training_metrics_speed_conversion_factor: float = 3.6  # m/s to km/h

    # Prometheus Monitoring
    prometheus_enabled: bool = False
    prometheus_port: int = 8001

    # CORS Configuration
    cors_origins: list[str] = ["*"]

    # Server Configuration
    server_workers: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()
