import torch
from loguru import logger
from typing import Optional
from contextlib import contextmanager


class GPUManager:
    """
    GPU 显存管理器
    确保 CV 模型串行加载，避免显存溢出
    """

    _current_model: Optional[str] = None

    @classmethod
    def get_device(cls) -> torch.device:
        """获取可用设备"""
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    @classmethod
    def get_gpu_info(cls) -> dict:
        """获取 GPU 信息"""
        if not torch.cuda.is_available():
            return {"available": False}

        return {
            "available": True,
            "device_name": torch.cuda.get_device_name(0),
            "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
            "allocated_memory_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2),
            "cached_memory_gb": round(torch.cuda.memory_reserved(0) / 1e9, 2),
        }

    @classmethod
    @contextmanager
    def load_model(cls, model_name: str):
        """
        上下文管理器：加载模型前卸载当前模型

        使用方式：
            with GPUManager.load_model("BlurBall"):
                model = load_blurball()
                result = model.predict(...)
        """
        if cls._current_model and cls._current_model != model_name:
            logger.info(f"卸载模型: {cls._current_model}")
            cls.clear_cache()

        cls._current_model = model_name
        logger.info(f"加载模型: {model_name}")

        try:
            yield
        finally:
            cls.clear_cache()

    @classmethod
    def clear_cache(cls):
        """清理 GPU 缓存"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.debug("已清理 GPU 缓存")
