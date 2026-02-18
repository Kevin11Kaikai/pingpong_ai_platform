"""
知识图谱服务
管理知识点和知识点关系
"""

from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.learning_resources.models import (
    KnowledgePoint, KnowledgeRelation, TechniqueCategory, DifficultyLevel,
)
from app.learning_resources.schemas import (
    KnowledgePointCreate, KnowledgePointUpdate, KnowledgeRelationCreate,
)
from app.shared.embedding_service import EmbeddingService


class KnowledgeService:
    """知识图谱服务"""

    async def create_knowledge_point(
        self,
        db: AsyncSession,
        data: KnowledgePointCreate,
    ) -> KnowledgePoint:
        """
        创建知识点

        Args:
            db: 数据库会话
            data: 创建请求数据

        Returns:
            创建的知识点对象
        """
        # 计算层级
        level = 0
        if data.parent_id:
            parent = await self.get_knowledge_point(db, data.parent_id)
            if parent:
                level = parent.level + 1

        point = KnowledgePoint(
            id=str(uuid.uuid4()),
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            category=TechniqueCategory(data.category),
            difficulty_level=DifficultyLevel(data.difficulty_level) if data.difficulty_level else None,
            parent_id=data.parent_id,
            level=level,
            sort_order=data.sort_order,
            definition=data.definition,
            key_points=data.key_points,
            common_mistakes=data.common_mistakes,
            tips=data.tips,
            resource_ids=data.resource_ids,
            resource_count=len(data.resource_ids) if data.resource_ids else 0,
        )

        # 生成嵌入向量
        text_parts = [data.display_name]
        if data.description:
            text_parts.append(data.description)
        if data.definition:
            text_parts.append(data.definition)
        if data.key_points:
            text_parts.extend(data.key_points)
        point.embedding = EmbeddingService.encode_single(" ".join(text_parts)).tolist()

        db.add(point)
        await db.flush()
        logger.info(f"创建知识点: {point.id} - {point.display_name}")
        return point

    async def get_knowledge_point(
        self,
        db: AsyncSession,
        point_id: str,
    ) -> Optional[KnowledgePoint]:
        """获取知识点详情"""
        result = await db.execute(
            select(KnowledgePoint).where(KnowledgePoint.id == point_id)
        )
        return result.scalar_one_or_none()

    async def get_knowledge_point_by_name(
        self,
        db: AsyncSession,
        name: str,
    ) -> Optional[KnowledgePoint]:
        """按名称获取知识点"""
        result = await db.execute(
            select(KnowledgePoint).where(KnowledgePoint.name == name)
        )
        return result.scalar_one_or_none()

    async def update_knowledge_point(
        self,
        db: AsyncSession,
        point_id: str,
        data: KnowledgePointUpdate,
    ) -> Optional[KnowledgePoint]:
        """更新知识点"""
        point = await self.get_knowledge_point(db, point_id)
        if not point:
            return None

        update_fields = data.model_dump(exclude_unset=True)
        rebuild_embedding = False

        for field, value in update_fields.items():
            if field == "category" and value is not None:
                value = TechniqueCategory(value)
            elif field == "difficulty_level" and value is not None:
                value = DifficultyLevel(value) if value else None
            setattr(point, field, value)
            if field in ("display_name", "description", "definition", "key_points"):
                rebuild_embedding = True

        # 更新资源计数
        if "resource_ids" in update_fields:
            point.resource_count = len(point.resource_ids) if point.resource_ids else 0

        # 重建嵌入向量
        if rebuild_embedding:
            text_parts = [point.display_name]
            if point.description:
                text_parts.append(point.description)
            if point.definition:
                text_parts.append(point.definition)
            if point.key_points:
                text_parts.extend(point.key_points)
            point.embedding = EmbeddingService.encode_single(" ".join(text_parts)).tolist()

        point.updated_at = datetime.utcnow()
        await db.flush()
        logger.info(f"更新知识点: {point_id}")
        return point

    async def delete_knowledge_point(
        self,
        db: AsyncSession,
        point_id: str,
    ) -> bool:
        """删除知识点"""
        point = await self.get_knowledge_point(db, point_id)
        if not point:
            return False
        await db.delete(point)
        await db.flush()
        logger.info(f"删除知识点: {point_id}")
        return True

    async def list_knowledge_points(
        self,
        db: AsyncSession,
        category: Optional[TechniqueCategory] = None,
        parent_id: Optional[str] = None,
        is_active: bool = True,
    ) -> List[KnowledgePoint]:
        """获取知识点列表"""
        conditions = [KnowledgePoint.is_active == is_active]

        if category:
            conditions.append(KnowledgePoint.category == category)
        if parent_id is not None:
            conditions.append(KnowledgePoint.parent_id == parent_id)

        stmt = (
            select(KnowledgePoint)
            .where(and_(*conditions))
            .order_by(KnowledgePoint.sort_order, KnowledgePoint.display_name)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_knowledge_tree(
        self,
        db: AsyncSession,
        category: Optional[TechniqueCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取知识点树结构

        Returns:
            树形结构的知识点列表
        """
        # 获取所有知识点
        points = await self.list_knowledge_points(db, category=category, parent_id=None)

        async def build_tree(parent_id: Optional[str]) -> List[Dict[str, Any]]:
            children = await self.list_knowledge_points(db, category=category, parent_id=parent_id)
            result = []
            for child in children:
                node = {
                    "id": child.id,
                    "name": child.name,
                    "display_name": child.display_name,
                    "category": child.category.value if child.category else None,
                    "level": child.level,
                    "resource_count": child.resource_count,
                    "children": await build_tree(child.id),
                }
                result.append(node)
            return result

        # 构建根节点
        root_nodes = []
        for point in points:
            if point.parent_id is None:
                node = {
                    "id": point.id,
                    "name": point.name,
                    "display_name": point.display_name,
                    "category": point.category.value if point.category else None,
                    "level": point.level,
                    "resource_count": point.resource_count,
                    "children": await build_tree(point.id),
                }
                root_nodes.append(node)

        return root_nodes

    async def add_relation(
        self,
        db: AsyncSession,
        data: KnowledgeRelationCreate,
    ) -> KnowledgeRelation:
        """添加知识点关系"""
        # 检查知识点是否存在
        from_point = await self.get_knowledge_point(db, data.from_point_id)
        to_point = await self.get_knowledge_point(db, data.to_point_id)

        if not from_point or not to_point:
            raise ValueError("知识点不存在")

        # 检查是否已存在相同关系
        existing = await db.execute(
            select(KnowledgeRelation).where(
                and_(
                    KnowledgeRelation.from_point_id == data.from_point_id,
                    KnowledgeRelation.to_point_id == data.to_point_id,
                    KnowledgeRelation.relation_type == data.relation_type,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("关系已存在")

        relation = KnowledgeRelation(
            id=str(uuid.uuid4()),
            from_point_id=data.from_point_id,
            to_point_id=data.to_point_id,
            relation_type=data.relation_type,
            weight=data.weight,
            description=data.description,
        )

        db.add(relation)
        await db.flush()
        logger.info(f"创建知识点关系: {data.from_point_id} -> {data.to_point_id} ({data.relation_type})")
        return relation

    async def delete_relation(
        self,
        db: AsyncSession,
        relation_id: str,
    ) -> bool:
        """删除知识点关系"""
        result = await db.execute(
            select(KnowledgeRelation).where(KnowledgeRelation.id == relation_id)
        )
        relation = result.scalar_one_or_none()
        if not relation:
            return False
        await db.delete(relation)
        await db.flush()
        return True

    async def get_knowledge_graph(
        self,
        db: AsyncSession,
        center_point_id: Optional[str] = None,
        category: Optional[TechniqueCategory] = None,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        获取知识图谱

        Args:
            db: 数据库会话
            center_point_id: 中心知识点 ID（可选）
            category: 限定分类（可选）
            depth: 展开深度

        Returns:
            包含节点和边的图谱数据
        """
        nodes = []
        edges = []
        visited_ids = set()

        if center_point_id:
            # 从中心点展开
            await self._expand_graph(db, center_point_id, depth, visited_ids, nodes, edges)
        else:
            # 获取所有节点
            conditions = [KnowledgePoint.is_active == True]
            if category:
                conditions.append(KnowledgePoint.category == category)

            result = await db.execute(
                select(KnowledgePoint).where(and_(*conditions))
            )
            all_points = result.scalars().all()

            for point in all_points:
                nodes.append({
                    "id": point.id,
                    "name": point.name,
                    "display_name": point.display_name,
                    "category": point.category.value if point.category else None,
                    "difficulty_level": point.difficulty_level.value if point.difficulty_level else None,
                    "level": point.level,
                    "resource_count": point.resource_count,
                })

            # 获取所有关系
            point_ids = [p.id for p in all_points]
            if point_ids:
                rel_result = await db.execute(
                    select(KnowledgeRelation)
                    .options(
                        selectinload(KnowledgeRelation.from_point),
                        selectinload(KnowledgeRelation.to_point),
                    )
                    .where(
                        or_(
                            KnowledgeRelation.from_point_id.in_(point_ids),
                            KnowledgeRelation.to_point_id.in_(point_ids),
                        )
                    )
                )
                relations = rel_result.scalars().all()

                for rel in relations:
                    edges.append({
                        "id": rel.id,
                        "from_point_id": rel.from_point_id,
                        "to_point_id": rel.to_point_id,
                        "relation_type": rel.relation_type,
                        "weight": rel.weight,
                        "description": rel.description,
                        "from_point_name": rel.from_point.display_name if rel.from_point else None,
                        "to_point_name": rel.to_point.display_name if rel.to_point else None,
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    async def _expand_graph(
        self,
        db: AsyncSession,
        point_id: str,
        depth: int,
        visited: set,
        nodes: list,
        edges: list,
    ) -> None:
        """递归展开图谱"""
        if depth <= 0 or point_id in visited:
            return

        visited.add(point_id)

        point = await self.get_knowledge_point(db, point_id)
        if not point:
            return

        nodes.append({
            "id": point.id,
            "name": point.name,
            "display_name": point.display_name,
            "category": point.category.value if point.category else None,
            "difficulty_level": point.difficulty_level.value if point.difficulty_level else None,
            "level": point.level,
            "resource_count": point.resource_count,
        })

        # 获取相关关系
        rel_result = await db.execute(
            select(KnowledgeRelation)
            .options(
                selectinload(KnowledgeRelation.from_point),
                selectinload(KnowledgeRelation.to_point),
            )
            .where(
                or_(
                    KnowledgeRelation.from_point_id == point_id,
                    KnowledgeRelation.to_point_id == point_id,
                )
            )
        )
        relations = rel_result.scalars().all()

        for rel in relations:
            edges.append({
                "id": rel.id,
                "from_point_id": rel.from_point_id,
                "to_point_id": rel.to_point_id,
                "relation_type": rel.relation_type,
                "weight": rel.weight,
                "description": rel.description,
                "from_point_name": rel.from_point.display_name if rel.from_point else None,
                "to_point_name": rel.to_point.display_name if rel.to_point else None,
            })

            # 递归展开相邻节点
            next_id = rel.to_point_id if rel.from_point_id == point_id else rel.from_point_id
            await self._expand_graph(db, next_id, depth - 1, visited, nodes, edges)

    async def get_prerequisites(
        self,
        db: AsyncSession,
        point_id: str,
    ) -> List[KnowledgePoint]:
        """获取前置知识点"""
        result = await db.execute(
            select(KnowledgeRelation)
            .options(selectinload(KnowledgeRelation.from_point))
            .where(
                and_(
                    KnowledgeRelation.to_point_id == point_id,
                    KnowledgeRelation.relation_type == "prerequisite",
                )
            )
        )
        relations = result.scalars().all()
        return [rel.from_point for rel in relations if rel.from_point]

    async def get_related_knowledge(
        self,
        db: AsyncSession,
        point_id: str,
    ) -> List[Tuple[KnowledgePoint, str, float]]:
        """
        获取相关知识点

        Returns:
            列表: (知识点, 关系类型, 权重)
        """
        result = await db.execute(
            select(KnowledgeRelation)
            .options(
                selectinload(KnowledgeRelation.from_point),
                selectinload(KnowledgeRelation.to_point),
            )
            .where(
                or_(
                    KnowledgeRelation.from_point_id == point_id,
                    KnowledgeRelation.to_point_id == point_id,
                )
            )
        )
        relations = result.scalars().all()

        related = []
        for rel in relations:
            if rel.from_point_id == point_id and rel.to_point:
                related.append((rel.to_point, rel.relation_type, rel.weight))
            elif rel.to_point_id == point_id and rel.from_point:
                related.append((rel.from_point, rel.relation_type, rel.weight))

        return related

    async def search_knowledge_points(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[Tuple[KnowledgePoint, float]]:
        """语义搜索知识点"""
        import numpy as np

        query_vec = EmbeddingService.encode_single(query)

        result = await db.execute(
            select(KnowledgePoint).where(
                and_(
                    KnowledgePoint.is_active == True,
                    KnowledgePoint.embedding.isnot(None),
                )
            )
        )
        points = result.scalars().all()

        if not points:
            return []

        # 计算相似度
        results = []
        for point in points:
            if point.embedding is None:
                continue
            emb = np.array(point.embedding, dtype=np.float32)
            score = float(np.dot(query_vec, emb) / (np.linalg.norm(query_vec) * np.linalg.norm(emb) + 1e-8))
            if score >= min_score:
                results.append((point, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# 服务单例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识服务单例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
