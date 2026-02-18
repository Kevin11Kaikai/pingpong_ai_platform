"""
向量存储模块
使用 FAISS 实现文档索引和检索
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
import numpy as np
import faiss
from loguru import logger

from app.shared.embedding_service import EmbeddingService
from app.shared.utils import get_project_root
from app.llm.core.document_processor import DocumentChunk


@dataclass
class ChunkMetadata:
    """块元数据"""
    content: str
    source: str
    chunk_index: int
    title: Optional[str] = None


@dataclass
class SearchResult:
    """搜索结果"""
    content: str
    source: str
    chunk_index: int
    score: float
    title: Optional[str] = None


class VectorStore:
    """
    FAISS 向量存储管理
    支持文档索引、检索和持久化
    """

    EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 输出维度

    def __init__(self, index_dir: Optional[Path] = None):
        """
        初始化向量存储

        Args:
            index_dir: 索引存储目录，默认为 app/vectorstore/
        """
        if index_dir is None:
            index_dir = get_project_root() / "app" / "vectorstore"
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "faiss_index.bin"
        self.metadata_path = self.index_dir / "metadata.json"

        self.index: Optional[faiss.Index] = None
        self.metadata: List[ChunkMetadata] = []

        # 确保目录存在
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        """加载已有索引，不存在则创建空索引"""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metadata = [ChunkMetadata(**item) for item in data]
                logger.info(f"加载向量索引完成，共 {len(self.metadata)} 条记录")
            except Exception as e:
                logger.warning(f"加载索引失败，创建新索引: {e}")
                self._create_empty_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self) -> None:
        """创建空索引"""
        self.index = faiss.IndexFlatIP(self.EMBEDDING_DIM)  # 内积相似度
        self.metadata = []
        logger.info("创建新的空向量索引")

    def save(self) -> None:
        """持久化索引到磁盘"""
        if self.index is None:
            logger.warning("索引未初始化，无法保存")
            return

        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            data = [asdict(m) for m in self.metadata]
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"向量索引已保存，共 {len(self.metadata)} 条记录")

    def add_documents(self, chunks: List[DocumentChunk]) -> int:
        """
        添加文档块到索引

        Args:
            chunks: 文档块列表

        Returns:
            添加的文档数量
        """
        if self.index is None:
            self.load()

        if not chunks:
            return 0

        # 提取文本并编码
        texts = [chunk.content for chunk in chunks]
        embeddings = EmbeddingService.encode(texts)

        # 归一化向量（用于内积相似度）
        faiss.normalize_L2(embeddings)

        # 添加到索引
        self.index.add(embeddings)

        # 保存元数据
        for chunk in chunks:
            meta = ChunkMetadata(
                content=chunk.content,
                source=chunk.source,
                chunk_index=chunk.chunk_index,
                title=chunk.title,
            )
            self.metadata.append(meta)

        logger.info(f"添加 {len(chunks)} 个文档块到索引")
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ) -> List[SearchResult]:
        """
        相似度搜索

        Args:
            query: 查询文本
            top_k: 返回数量
            score_threshold: 分数阈值（内积，0-1）

        Returns:
            搜索结果列表
        """
        if self.index is None:
            self.load()

        if self.index.ntotal == 0:
            logger.debug("索引为空，返回空结果")
            return []

        # 编码查询
        query_embedding = EmbeddingService.encode_single(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)

        # 搜索
        actual_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, actual_k)

        # 构建结果
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or score < score_threshold:
                continue
            meta = self.metadata[idx]
            result = SearchResult(
                content=meta.content,
                source=meta.source,
                chunk_index=meta.chunk_index,
                score=float(score),
                title=meta.title,
            )
            results.append(result)

        logger.debug(f"搜索完成，查询: '{query[:50]}...'，找到 {len(results)} 条结果")
        return results

    def delete_by_source(self, source: str) -> int:
        """
        按文档来源删除

        注意：FAISS IndexFlatIP 不支持直接删除，需要重建索引

        Args:
            source: 文档来源标识

        Returns:
            删除的文档块数量
        """
        if self.index is None:
            self.load()

        # 找出要保留的索引
        keep_indices = []
        delete_count = 0
        for i, meta in enumerate(self.metadata):
            if meta.source == source:
                delete_count += 1
            else:
                keep_indices.append(i)

        if delete_count == 0:
            return 0

        # 重建索引
        if keep_indices:
            # 获取要保留的向量
            # 由于 IndexFlatIP 支持 reconstruct，我们可以重建
            new_index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
            new_metadata = []

            for i in keep_indices:
                vector = self.index.reconstruct(i)
                new_index.add(vector.reshape(1, -1))
                new_metadata.append(self.metadata[i])

            self.index = new_index
            self.metadata = new_metadata
        else:
            self._create_empty_index()

        logger.info(f"删除来源 '{source}' 的 {delete_count} 个文档块")
        return delete_count

    def get_stats(self) -> dict:
        """获取索引统计信息"""
        if self.index is None:
            self.load()

        sources = {}
        for meta in self.metadata:
            sources[meta.source] = sources.get(meta.source, 0) + 1

        return {
            "total_chunks": self.index.ntotal if self.index else 0,
            "unique_sources": len(sources),
            "sources": sources,
        }

    def clear(self) -> None:
        """清空索引"""
        self._create_empty_index()
        self.save()
        logger.info("向量索引已清空")


# 单例实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.load()
    return _vector_store
