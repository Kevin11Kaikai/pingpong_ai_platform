"""
知识图谱 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shared.database import get_db_session
from app.learning_resources.core import get_knowledge_service
from app.learning_resources.models import TechniqueCategory
from app.learning_resources.schemas import (
    KnowledgePointCreate, KnowledgePointUpdate, KnowledgePointResponse,
    KnowledgePointBrief, KnowledgeRelationCreate, KnowledgeRelationResponse,
    KnowledgeGraphResponse,
)

router = APIRouter()


@router.post("", response_model=KnowledgePointResponse)
async def create_knowledge_point(
    data: KnowledgePointCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建知识点

    创建新的知识图谱节点，支持设置父节点形成层级结构。
    """
    service = get_knowledge_service()
    try:
        point = await service.create_knowledge_point(db, data)
        return KnowledgePointResponse.model_validate(point)
    except Exception as e:
        logger.error(f"创建知识点失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{point_id}", response_model=KnowledgePointResponse)
async def get_knowledge_point(
    point_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取知识点详情

    返回知识点的完整信息，包括定义、要点、常见错误等。
    """
    service = get_knowledge_service()
    point = await service.get_knowledge_point(db, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return KnowledgePointResponse.model_validate(point)


@router.put("/{point_id}", response_model=KnowledgePointResponse)
async def update_knowledge_point(
    point_id: str,
    data: KnowledgePointUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新知识点

    更新知识点的信息，支持部分更新。
    """
    service = get_knowledge_service()
    point = await service.update_knowledge_point(db, point_id, data)
    if not point:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return KnowledgePointResponse.model_validate(point)


@router.delete("/{point_id}")
async def delete_knowledge_point(
    point_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除知识点

    删除知识点及其相关的关系。
    """
    service = get_knowledge_service()
    success = await service.delete_knowledge_point(db, point_id)
    if not success:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return {"message": "删除成功"}


@router.get("", response_model=list[KnowledgePointBrief])
async def list_knowledge_points(
    category: str = Query(None, description="技术分类过滤"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取知识点列表

    返回所有活跃的知识点列表，支持按分类过滤。
    """
    service = get_knowledge_service()
    cat = TechniqueCategory(category) if category else None
    points = await service.list_knowledge_points(db, category=cat)
    return [KnowledgePointBrief.model_validate(p) for p in points]


@router.get("/tree", response_model=list)
async def get_knowledge_tree(
    category: str = Query(None, description="技术分类过滤"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取知识点树结构

    返回层级结构的知识点树，适合展示知识体系。
    """
    service = get_knowledge_service()
    cat = TechniqueCategory(category) if category else None
    tree = await service.get_knowledge_tree(db, category=cat)
    return tree


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    center_id: str = Query(None, description="中心知识点 ID"),
    category: str = Query(None, description="技术分类过滤"),
    depth: int = Query(2, ge=1, le=5, description="展开深度"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取知识图谱

    返回包含节点和边的知识图谱数据，适合可视化展示。
    """
    service = get_knowledge_service()
    cat = TechniqueCategory(category) if category else None
    graph = await service.get_knowledge_graph(
        db, center_point_id=center_id, category=cat, depth=depth
    )
    return graph


@router.post("/relations", response_model=KnowledgeRelationResponse)
async def add_knowledge_relation(
    data: KnowledgeRelationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    添加知识点关系

    创建两个知识点之间的关系（前置、相关、扩展等）。
    """
    service = get_knowledge_service()
    try:
        relation = await service.add_relation(db, data)

        # 获取知识点名称
        from_point = await service.get_knowledge_point(db, relation.from_point_id)
        to_point = await service.get_knowledge_point(db, relation.to_point_id)

        return KnowledgeRelationResponse(
            id=relation.id,
            from_point_id=relation.from_point_id,
            to_point_id=relation.to_point_id,
            relation_type=relation.relation_type,
            weight=relation.weight,
            description=relation.description,
            from_point_name=from_point.display_name if from_point else None,
            to_point_name=to_point.display_name if to_point else None,
            created_at=relation.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/relations/{relation_id}")
async def delete_knowledge_relation(
    relation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除知识点关系
    """
    service = get_knowledge_service()
    success = await service.delete_relation(db, relation_id)
    if not success:
        raise HTTPException(status_code=404, detail="关系不存在")
    return {"message": "删除成功"}


@router.get("/{point_id}/prerequisites", response_model=list[KnowledgePointBrief])
async def get_prerequisites(
    point_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取前置知识点

    返回学习当前知识点之前需要掌握的前置知识。
    """
    service = get_knowledge_service()
    prereqs = await service.get_prerequisites(db, point_id)
    return [KnowledgePointBrief.model_validate(p) for p in prereqs]


@router.get("/{point_id}/related", response_model=list)
async def get_related_knowledge(
    point_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取相关知识点

    返回与当前知识点相关的所有知识点及其关系类型。
    """
    service = get_knowledge_service()
    related = await service.get_related_knowledge(db, point_id)
    return [
        {
            "point": KnowledgePointBrief.model_validate(point),
            "relation_type": rel_type,
            "weight": weight,
        }
        for point, rel_type, weight in related
    ]


@router.post("/search")
async def search_knowledge_points(
    query: str = Query(..., min_length=1, description="搜索查询"),
    top_k: int = Query(10, ge=1, le=50, description="返回数量"),
    min_score: float = Query(0.3, ge=0, le=1, description="最低相似度"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    语义搜索知识点

    使用向量相似度搜索相关知识点。
    """
    service = get_knowledge_service()
    results = await service.search_knowledge_points(db, query, top_k, min_score)
    return [
        {
            "point": KnowledgePointBrief.model_validate(point),
            "score": score,
        }
        for point, score in results
    ]
