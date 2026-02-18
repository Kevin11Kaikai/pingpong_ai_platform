from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()
