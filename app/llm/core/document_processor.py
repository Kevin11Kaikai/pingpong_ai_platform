"""
文档处理器模块
实现文档分块和预处理
"""

import re
import hashlib
from typing import List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class DocumentChunk:
    """文档块数据类"""
    content: str
    source: str
    chunk_index: int
    title: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentProcessor:
    """
    文档预处理器
    支持文本分块、清洗
    """

    DEFAULT_CHUNK_SIZE = 500  # 字符
    DEFAULT_CHUNK_OVERLAP = 50

    @staticmethod
    def clean_text(text: str) -> str:
        """
        文本清洗

        - 去除多余空白
        - 规范化换行符
        - 去除特殊控制字符
        """
        # 替换多个空白为单个空格
        text = re.sub(r"[ \t]+", " ", text)
        # 规范化换行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行首尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # 去除首尾空白
        return text.strip()

    @classmethod
    def chunk_text(
        cls,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[str]:
        """
        文本分块

        使用滑动窗口策略，保留上下文连贯性
        优先在句子边界分割

        Args:
            text: 待分块文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小（字符数）

        Returns:
            文本块列表
        """
        if not text:
            return []

        # 清洗文本
        text = cls.clean_text(text)

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # 计算结束位置
            end = start + chunk_size

            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 在 chunk 范围内寻找句子结束符
                sentence_ends = [
                    text.rfind("。", start, end),
                    text.rfind("！", start, end),
                    text.rfind("？", start, end),
                    text.rfind(".", start, end),
                    text.rfind("!", start, end),
                    text.rfind("?", start, end),
                    text.rfind("\n", start, end),
                ]
                # 找最后一个有效的句子结束位置
                best_end = max(sentence_ends)
                if best_end > start + chunk_size // 2:
                    end = best_end + 1  # 包含句号

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 下一块的起始位置，考虑重叠
            start = end - overlap
            if start < 0:
                start = end

        logger.debug(f"文本分块完成，共 {len(chunks)} 块")
        return chunks

    @staticmethod
    def compute_hash(content: str) -> str:
        """计算内容的 SHA256 哈希值"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @classmethod
    def process_document(
        cls,
        content: str,
        source: str,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[DocumentChunk]:
        """
        完整文档处理流程

        Args:
            content: 文档内容
            source: 来源标识（文件名或URL）
            title: 文档标题
            metadata: 额外元数据
            chunk_size: 块大小
            chunk_overlap: 重叠大小

        Returns:
            文档块列表
        """
        # 分块
        chunks = cls.chunk_text(content, chunk_size, chunk_overlap)

        # 创建 DocumentChunk 对象
        result = []
        for i, chunk_content in enumerate(chunks):
            chunk = DocumentChunk(
                content=chunk_content,
                source=source,
                chunk_index=i,
                title=title,
                metadata=metadata,
            )
            result.append(chunk)

        logger.info(f"文档处理完成: {source}，共 {len(result)} 块")
        return result
