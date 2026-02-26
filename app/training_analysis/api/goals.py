"""
训练目标 API 路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.training_analysis.core import get_goal_service
from app.training_analysis.schemas import (
    GoalCreate, GoalUpdate, GoalResponse, GoalListResponse, MilestoneCreate
)

router = APIRouter()


@router.post("", response_model=GoalResponse)
async def create_goal(
    data: GoalCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建训练目标

    设定速度、准确率、训练次数等目标。
    """
    service = get_goal_service()
    goal = await service.create_goal(db, data)
    return GoalResponse.model_validate(goal)


@router.get("", response_model=GoalListResponse)
async def list_goals(
    user_id: str = Query(..., description="用户ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    goal_type: Optional[str] = Query(None, description="类型筛选"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户目标列表

    支持按状态和类型筛选。
    """
    service = get_goal_service()
    goals = await service.list_user_goals(db, user_id, status, goal_type)

    return GoalListResponse(
        goals=[GoalResponse.model_validate(g) for g in goals],
        total=len(goals),
    )


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取目标详情

    包含目标信息、进度和里程碑。
    """
    service = get_goal_service()
    goal = await service.get_goal(db, goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")

    return GoalResponse.model_validate(goal)


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    data: GoalUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新训练目标

    可更新目标值、截止日期和状态。
    """
    service = get_goal_service()
    goal = await service.update_goal(db, goal_id, data)

    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")

    return GoalResponse.model_validate(goal)


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除训练目标
    """
    service = get_goal_service()
    success = await service.delete_goal(db, goal_id)

    if not success:
        raise HTTPException(status_code=404, detail="目标不存在")

    return {"message": "目标已删除", "goal_id": goal_id}


@router.post("/{goal_id}/refresh", response_model=GoalResponse)
async def refresh_goal_progress(
    goal_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    刷新目标进度

    根据最新训练数据重新计算目标进度。
    """
    service = get_goal_service()
    goal = await service.update_goal_progress(db, goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")

    return GoalResponse.model_validate(goal)


@router.post("/{goal_id}/milestones", response_model=GoalResponse)
async def add_milestone(
    goal_id: str,
    data: MilestoneCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """
    添加目标里程碑

    记录目标进度中的重要节点。
    """
    service = get_goal_service()
    goal = await service.add_milestone(db, goal_id, data)

    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")

    return GoalResponse.model_validate(goal)


@router.get("/user/{user_id}/active", response_model=list[GoalResponse])
async def get_active_goals(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户活跃目标

    返回所有进行中的目标。
    """
    service = get_goal_service()
    goals = await service.list_user_goals(db, user_id, status="active")

    return [GoalResponse.model_validate(g) for g in goals]


@router.get("/user/{user_id}/achieved", response_model=list[GoalResponse])
async def get_achieved_goals(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取用户已达成目标

    返回所有已完成的目标。
    """
    service = get_goal_service()
    goals = await service.list_user_goals(db, user_id, status="achieved")

    return [GoalResponse.model_validate(g) for g in goals]


@router.post("/check-achievements")
async def check_achievements(
    user_id: str = Query(..., description="用户ID"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    检查目标达成情况

    扫描用户所有活跃目标，返回新达成的目标。
    """
    service = get_goal_service()
    achieved = await service.check_goal_achievements(db, user_id)

    return {
        "user_id": user_id,
        "newly_achieved": [GoalResponse.model_validate(g) for g in achieved],
        "count": len(achieved),
    }
