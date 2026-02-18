"""
基础架构测试模块 (Phase 1)
测试配置、数据库、GPU管理器、Embedding服务等基础组件
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np


# ========== 配置测试 ==========

class TestSettings:
    """配置模块测试"""

    def test_settings_import(self):
        """测试配置模块导入"""
        from config.settings import Settings, get_settings
        assert Settings is not None
        assert get_settings is not None

    def test_settings_fields(self):
        """测试配置字段定义"""
        from config.settings import Settings
        # 检查必要字段存在
        fields = Settings.model_fields
        assert "llm_api_key" in fields
        assert "llm_base_url" in fields
        assert "database_url" in fields
        assert "jwt_secret_key" in fields

    def test_settings_defaults(self):
        """测试默认配置值"""
        from config.settings import Settings
        fields = Settings.model_fields
        # 检查默认值
        assert fields["llm_base_url"].default == "https://api.ohmygpt.com/v1"
        assert fields["app_env"].default == "development"
        assert fields["debug"].default is True

    @patch.dict("os.environ", {
        "LLM_API_KEY": "test-key",
        "JWT_SECRET_KEY": "test-secret",
    })
    def test_settings_from_env(self):
        """测试从环境变量加载配置"""
        from config.settings import Settings
        settings = Settings()
        assert settings.llm_api_key == "test-key"
        assert settings.jwt_secret_key == "test-secret"


# ========== GPU 管理器测试 ==========

class TestGPUManager:
    """GPU 管理器测试"""

    def test_gpu_manager_import(self):
        """测试 GPU 管理器导入"""
        from app.shared.gpu_manager import GPUManager
        assert GPUManager is not None

    def test_get_device(self):
        """测试获取设备"""
        from app.shared.gpu_manager import GPUManager
        import torch
        device = GPUManager.get_device()
        assert isinstance(device, torch.device)
        assert device.type in ["cuda", "cpu"]

    def test_get_gpu_info(self):
        """测试获取 GPU 信息"""
        from app.shared.gpu_manager import GPUManager
        info = GPUManager.get_gpu_info()
        assert "available" in info
        if info["available"]:
            assert "device_name" in info
            assert "total_memory_gb" in info
            assert "allocated_memory_gb" in info
            assert "cached_memory_gb" in info

    def test_load_model_context_manager(self):
        """测试模型加载上下文管理器"""
        from app.shared.gpu_manager import GPUManager
        with GPUManager.load_model("TestModel"):
            assert GPUManager._current_model == "TestModel"
        # 清理后 _current_model 仍然保持（只清 cache）

    def test_clear_cache(self):
        """测试清理 GPU 缓存"""
        from app.shared.gpu_manager import GPUManager
        # 不应抛出异常
        GPUManager.clear_cache()


# ========== Embedding 服务测试 ==========

class TestEmbeddingService:
    """Embedding 服务测试"""

    def test_embedding_service_import(self):
        """测试 Embedding 服务导入"""
        from app.shared.embedding_service import EmbeddingService
        assert EmbeddingService is not None
        assert EmbeddingService.MODEL_NAME == "all-MiniLM-L6-v2"

    def test_embedding_dimension(self):
        """测试 Embedding 维度"""
        from app.shared.embedding_service import EmbeddingService
        # all-MiniLM-L6-v2 输出维度应为 384
        result = EmbeddingService.encode(["test"])
        assert result.shape[1] == 384

    def test_encode_single(self):
        """测试单条文本编码"""
        from app.shared.embedding_service import EmbeddingService
        result = EmbeddingService.encode_single("Hello world")
        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)

    def test_encode_batch(self):
        """测试批量文本编码"""
        from app.shared.embedding_service import EmbeddingService
        texts = ["Hello", "World", "Test"]
        result = EmbeddingService.encode(texts)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 384)

    def test_embedding_similarity(self):
        """测试相似文本应有更高相似度"""
        from app.shared.embedding_service import EmbeddingService
        e1 = EmbeddingService.encode_single("乒乓球技术")
        e2 = EmbeddingService.encode_single("乒乓球训练")
        e3 = EmbeddingService.encode_single("完全无关的内容")

        # 计算余弦相似度
        sim_related = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        sim_unrelated = np.dot(e1, e3) / (np.linalg.norm(e1) * np.linalg.norm(e3))

        # 相关文本相似度应更高
        assert sim_related > sim_unrelated


# ========== 数据库测试 ==========

class TestDatabase:
    """数据库模块测试"""

    def test_database_import(self):
        """测试数据库模块导入"""
        from app.shared.database import (
            Base, get_engine, get_session_factory,
            get_db_session, init_db, close_db
        )
        assert Base is not None
        assert get_engine is not None
        assert get_session_factory is not None

    def test_base_class(self):
        """测试 ORM 基类"""
        from app.shared.database import Base
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


# ========== FastAPI 应用测试 ==========

class TestFastAPIApp:
    """FastAPI 应用测试"""

    def test_app_import(self):
        """测试应用导入"""
        from app.main import app
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_app_metadata(self):
        """测试应用元数据"""
        from app.main import app
        assert app.title == "Pingpong AI Platform"
        assert app.version == "0.1.0"

    def test_routers_registered(self):
        """测试路由注册"""
        from app.main import app
        routes = [route.path for route in app.routes]
        # 检查各模块路由前缀
        assert any("/api/llm" in r for r in routes)
        assert any("/api/ball-tracking" in r for r in routes)
        assert any("/api/equipment" in r for r in routes)
        assert any("/health" in r for r in routes)


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app, raise_server_exceptions=False)

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"


# ========== 工具函数测试 ==========

class TestUtils:
    """工具函数测试"""

    def test_get_project_root(self):
        """测试获取项目根目录"""
        from app.shared.utils import get_project_root
        from pathlib import Path
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.exists()
        # 应包含关键项目文件
        assert (root / "app").exists() or (root / "config").exists()
