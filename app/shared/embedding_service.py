from sentence_transformers import SentenceTransformer
from loguru import logger
from typing import List
import numpy as np


class EmbeddingService:
    """
    共享 Embedding 服务
    全模块复用，常驻内存（~0.5GB）
    """

    _model: SentenceTransformer = None
    MODEL_NAME = "all-MiniLM-L6-v2"

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """懒加载 Embedding 模型"""
        if cls._model is None:
            logger.info(f"加载 Embedding 模型: {cls.MODEL_NAME}")
            cls._model = SentenceTransformer(cls.MODEL_NAME)
        return cls._model

    @classmethod
    def encode(cls, texts: List[str]) -> np.ndarray:
        """
        文本向量化

        Args:
            texts: 待编码的文本列表

        Returns:
            numpy 数组，shape=(len(texts), 384)
        """
        model = cls.get_model()
        return model.encode(texts, convert_to_numpy=True)

    @classmethod
    def encode_single(cls, text: str) -> np.ndarray:
        """单条文本向量化"""
        return cls.encode([text])[0]
