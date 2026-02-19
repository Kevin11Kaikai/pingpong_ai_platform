"""
视频分析集成服务
与 ball_tracking 模块集成，分析教学视频中的技术动作
"""

from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.learning_resources.models import (
    VideoAnalysisLink, LearningResource, TechniqueCategory,
)
from app.learning_resources.schemas import (
    VideoAnalysisLinkCreate, TechniqueAnalysisRequest,
)


class VideoAnalysisService:
    """
    视频分析集成服务
    连接 learning_resources 和 ball_tracking 模块
    """

    # 技术动作标准参数（用于对比分析）
    TECHNIQUE_STANDARDS = {
        TechniqueCategory.FOREHAND: {
            "loop": {
                "ideal_speed_range": (20, 35),  # m/s
                "ideal_spin_rpm": 3000,
                "key_phases": ["准备", "引拍", "击球", "随挥"],
            },
            "drive": {
                "ideal_speed_range": (15, 25),
                "ideal_spin_rpm": 1500,
            },
            "smash": {
                "ideal_speed_range": (25, 40),
                "ideal_spin_rpm": 500,
            },
        },
        TechniqueCategory.BACKHAND: {
            "loop": {
                "ideal_speed_range": (18, 30),
                "ideal_spin_rpm": 2500,
            },
            "drive": {
                "ideal_speed_range": (12, 22),
                "ideal_spin_rpm": 1200,
            },
        },
        TechniqueCategory.SERVE: {
            "pendulum": {
                "ideal_spin_rpm": 4000,
                "key_phases": ["抛球", "引拍", "击球", "旋转发力"],
            },
            "reverse_pendulum": {
                "ideal_spin_rpm": 3500,
            },
            "tomahawk": {
                "ideal_spin_rpm": 3000,
            },
        },
    }

    async def create_link(
        self,
        db: AsyncSession,
        data: VideoAnalysisLinkCreate,
    ) -> VideoAnalysisLink:
        """
        创建视频分析关联

        Args:
            db: 数据库会话
            data: 关联数据

        Returns:
            创建的关联对象
        """
        # 验证资源存在
        resource_result = await db.execute(
            select(LearningResource).where(LearningResource.id == data.resource_id)
        )
        resource = resource_result.scalar_one_or_none()
        if not resource:
            raise ValueError(f"学习资源 {data.resource_id} 不存在")

        link = VideoAnalysisLink(
            id=str(uuid.uuid4()),
            resource_id=data.resource_id,
            ball_tracking_job_id=data.ball_tracking_job_id,
            start_time_seconds=data.start_time_seconds,
            end_time_seconds=data.end_time_seconds,
            analysis_type=data.analysis_type,
            technique_category=TechniqueCategory(data.technique_category) if data.technique_category else None,
        )

        db.add(link)
        await db.flush()
        logger.info(f"创建视频分析关联: {link.id} (resource={data.resource_id}, job={data.ball_tracking_job_id})")
        return link

    async def get_link(
        self,
        db: AsyncSession,
        link_id: str,
    ) -> Optional[VideoAnalysisLink]:
        """获取分析关联"""
        result = await db.execute(
            select(VideoAnalysisLink).where(VideoAnalysisLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def get_links_by_resource(
        self,
        db: AsyncSession,
        resource_id: str,
    ) -> List[VideoAnalysisLink]:
        """获取资源的所有视频分析关联"""
        result = await db.execute(
            select(VideoAnalysisLink)
            .where(VideoAnalysisLink.resource_id == resource_id)
            .order_by(VideoAnalysisLink.start_time_seconds)
        )
        return list(result.scalars().all())

    async def analyze_technique(
        self,
        db: AsyncSession,
        request: TechniqueAnalysisRequest,
    ) -> Dict[str, Any]:
        """
        分析教学视频中的技术动作

        流程:
        1. 获取/创建 VideoAnalysisLink
        2. 获取 ball_tracking 任务结果
        3. 与标准动作参数对比
        4. 生成 AI 解说（可选）

        Args:
            db: 数据库会话
            request: 分析请求

        Returns:
            分析结果
        """
        # 检查是否已存在分析关联
        existing_result = await db.execute(
            select(VideoAnalysisLink).where(
                and_(
                    VideoAnalysisLink.resource_id == request.resource_id,
                    VideoAnalysisLink.ball_tracking_job_id == request.ball_tracking_job_id,
                )
            )
        )
        link = existing_result.scalar_one_or_none()

        if not link:
            # 创建新关联
            link = VideoAnalysisLink(
                id=str(uuid.uuid4()),
                resource_id=request.resource_id,
                ball_tracking_job_id=request.ball_tracking_job_id,
                analysis_type="technique_demo",
                technique_category=TechniqueCategory(request.technique_category),
            )
            db.add(link)

        # 获取 ball_tracking 分析结果
        tracking_data = await self._get_ball_tracking_result(db, request.ball_tracking_job_id)

        # 执行对比分析
        analysis_summary, comparison_score, suggestions = await self._analyze_with_standards(
            technique_category=TechniqueCategory(request.technique_category),
            tracking_data=tracking_data,
        )

        # 更新分析结果
        link.analysis_summary = analysis_summary
        link.improvement_suggestions = suggestions
        link.updated_at = datetime.utcnow()

        # 生成 AI 解说
        ai_commentary = None
        if request.generate_commentary:
            ai_commentary = await self._generate_ai_commentary(
                technique_category=request.technique_category,
                analysis_summary=analysis_summary,
                suggestions=suggestions,
            )
            link.ai_commentary = ai_commentary

        await db.flush()

        return {
            "link_id": link.id,
            "resource_id": request.resource_id,
            "ball_tracking_job_id": request.ball_tracking_job_id,
            "technique_category": request.technique_category,
            "analysis_summary": analysis_summary,
            "ai_commentary": ai_commentary,
            "improvement_suggestions": suggestions,
            "comparison_score": comparison_score,
        }

    async def _get_ball_tracking_result(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取 ball_tracking 任务结果

        尝试从 ball_tracking 模块获取分析数据
        """
        try:
            from app.ball_tracking.models import ProcessingJob

            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.warning(f"ball_tracking 任务 {job_id} 不存在")
                return None

            # 返回基本信息（实际项目中可能需要获取更多轨迹数据）
            return {
                "job_id": job.id,
                "status": job.status,
                "video_width": getattr(job, 'video_width', None),
                "video_height": getattr(job, 'video_height', None),
                "video_fps": getattr(job, 'video_fps', None),
                "video_duration": getattr(job, 'video_duration', None),
            }
        except ImportError:
            logger.warning("ball_tracking 模块不可用")
            return None
        except Exception as e:
            logger.error(f"获取 ball_tracking 结果失败: {e}")
            return None

    async def _analyze_with_standards(
        self,
        technique_category: TechniqueCategory,
        tracking_data: Optional[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Optional[float], List[str]]:
        """
        与标准动作参数对比分析

        Returns:
            (分析摘要, 对比分数, 改进建议)
        """
        analysis_summary = {
            "technique_category": technique_category.value,
            "analysis_status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }

        suggestions = []
        comparison_score = None

        # 如果没有 tracking 数据，返回基础分析
        if not tracking_data:
            analysis_summary["note"] = "无 ball_tracking 数据，仅提供基础分析"
            suggestions.append("建议使用 ball_tracking 功能获取更精确的轨迹分析")
            return analysis_summary, comparison_score, suggestions

        # 获取该技术类型的标准参数
        standards = self.TECHNIQUE_STANDARDS.get(technique_category, {})

        if standards:
            analysis_summary["standards_available"] = True
            analysis_summary["technique_standards"] = {
                k: v for k, v in list(standards.items())[:3]  # 只返回部分标准
            }

            # 根据标准生成建议
            for technique_name, params in standards.items():
                if "key_phases" in params:
                    suggestions.append(f"{technique_name}的关键阶段: {', '.join(params['key_phases'])}")
                if "ideal_spin_rpm" in params:
                    suggestions.append(f"理想旋转量: {params['ideal_spin_rpm']} RPM")

            # 模拟对比分数（实际项目中需要根据 tracking_data 计算）
            comparison_score = 0.75  # 示例分数
        else:
            analysis_summary["standards_available"] = False
            suggestions.append("该技术类型暂无标准参数，建议参考教学视频进行自我对比")

        return analysis_summary, comparison_score, suggestions

    async def _generate_ai_commentary(
        self,
        technique_category: str,
        analysis_summary: Dict[str, Any],
        suggestions: List[str],
    ) -> str:
        """
        使用 RAG 生成 AI 技术解说

        实际项目中应调用 LLM 服务生成更详细的解说
        """
        try:
            from app.llm.core.rag_service import get_rag_service

            rag_service = get_rag_service()

            prompt = f"""请为以下乒乓球技术动作分析生成专业解说：

技术类型: {technique_category}
分析状态: {analysis_summary.get('analysis_status', 'unknown')}
改进建议: {'; '.join(suggestions[:3]) if suggestions else '暂无'}

请提供：
1. 该技术的要点说明（2-3句话）
2. 常见问题和改进方向
3. 练习建议
"""

            response = await rag_service.generate_with_context(
                query=prompt,
                use_rag=True,
                top_k=3,
            )

            return response.content

        except ImportError:
            logger.warning("RAG 服务不可用，使用默认解说")
            return self._get_default_commentary(technique_category, suggestions)
        except Exception as e:
            logger.error(f"生成 AI 解说失败: {e}")
            return self._get_default_commentary(technique_category, suggestions)

    def _get_default_commentary(
        self,
        technique_category: str,
        suggestions: List[str],
    ) -> str:
        """生成默认解说"""
        commentaries = {
            "forehand": "正手技术是乒乓球最基础也是最重要的进攻手段。注意保持稳定的击球点，充分利用腰腿发力。",
            "backhand": "反手技术需要良好的手腕控制和快速的反应。练习时注意拍形角度和击球时机。",
            "serve": "发球是比赛中唯一完全由自己控制的环节。掌握多种旋转变化是提高发球质量的关键。",
            "footwork": "步法是乒乓球运动的基础。良好的步法能让你始终处于最佳击球位置。",
            "spin": "旋转是乒乓球的灵魂。理解和掌握各种旋转的产生和应对方法是提高水平的必经之路。",
        }

        base_commentary = commentaries.get(technique_category, "持续练习是提高技术水平的最佳方式。")

        if suggestions:
            base_commentary += f"\n\n改进建议：{'; '.join(suggestions[:2])}"

        return base_commentary

    async def update_link_with_commentary(
        self,
        db: AsyncSession,
        link_id: str,
    ) -> Optional[VideoAnalysisLink]:
        """为已有的分析关联生成 AI 解说"""
        link = await self.get_link(db, link_id)
        if not link:
            return None

        technique_category = link.technique_category.value if link.technique_category else "forehand"

        ai_commentary = await self._generate_ai_commentary(
            technique_category=technique_category,
            analysis_summary=link.analysis_summary or {},
            suggestions=link.improvement_suggestions or [],
        )

        link.ai_commentary = ai_commentary
        link.updated_at = datetime.utcnow()
        await db.flush()

        return link


# 服务单例
_video_analysis_service: Optional[VideoAnalysisService] = None


def get_video_analysis_service() -> VideoAnalysisService:
    """获取视频分析服务单例"""
    global _video_analysis_service
    if _video_analysis_service is None:
        _video_analysis_service = VideoAnalysisService()
    return _video_analysis_service
