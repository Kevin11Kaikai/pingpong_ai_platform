"""
回复生成服务
基于 RAG 为社交媒体内容生成回复建议
"""

from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.social_media.models import SocialContent, ReplySuggestion, ContentStatus
from app.llm.core.rag_service import RAGService, get_rag_service
from app.llm.schemas import ChatMessage


# 回复风格模板
REPLY_STYLE_PROMPTS = {
    "professional": """你是一位专业的乒乓球教练，回复社交媒体上的问题。
请用专业但易懂的语言回答，必要时引用技术要点。
回复要有条理，可以使用编号列表。
确保回复准确、实用，能帮助提问者解决问题。""",

    "friendly": """你是一位热心的乒乓球爱好者，回复社交媒体上的问题。
请用亲切友好的语气回答，可以分享个人经验和心得。
语言要口语化，让人感到亲切和鼓励。
适当使用一些口语化表达，但保持专业性。""",

    "concise": """你是乒乓球专家，简洁回复问题。
回答要精炼，直击要点，不要啰嗦。
控制在 200 字以内，每句话都要有价值。
使用简短有力的句子。""",
}


class ReplyService:
    """
    回复生成服务
    使用 RAG 增强生成高质量回复
    """

    def __init__(self, rag_service: Optional[RAGService] = None):
        self.rag_service = rag_service or get_rag_service()

    async def generate_reply(
        self,
        db: AsyncSession,
        content_id: str,
        style: str = "professional",
        use_rag: bool = True,
        max_length: int = 500,
        temperature: float = 0.7,
    ) -> ReplySuggestion:
        """
        为指定内容生成回复建议

        Args:
            db: 数据库会话
            content_id: 内容 ID
            style: 回复风格 (professional, friendly, concise)
            use_rag: 是否使用 RAG 检索
            max_length: 最大长度
            temperature: 生成温度

        Returns:
            生成的回复建议
        """
        # 获取内容
        content = await self._get_content(db, content_id)
        if not content:
            raise ValueError(f"内容不存在: {content_id}")

        # 构建查询
        query = self._build_reply_query(content, max_length)

        # 获取风格提示
        style_prompt = REPLY_STYLE_PROMPTS.get(style, REPLY_STYLE_PROMPTS["professional"])

        # 使用 RAG 生成回复
        rag_response = await self.rag_service.generate_with_context(
            query=query,
            conversation_history=[
                ChatMessage(role="system", content=style_prompt),
            ],
            top_k=5,
            use_rag=use_rag,
            model="gpt-4o-mini",
            temperature=temperature,
            stream=False,
        )

        # 评估回复质量
        quality_score = self._evaluate_reply_quality(
            content.content,
            rag_response.content,
        )

        # 创建回复建议记录
        suggestion = ReplySuggestion(
            id=str(uuid.uuid4()),
            content_id=content_id,
            reply_content=rag_response.content,
            model_used="gpt-4o-mini",
            temperature=temperature,
            style=style,
            sources=rag_response.sources,
            quality_score=quality_score,
        )
        db.add(suggestion)

        # 更新内容状态
        if content.status == ContentStatus.ANALYZED:
            content.status = ContentStatus.REPLIED

        await db.flush()

        logger.info(f"生成回复: content_id={content_id}, style={style}, quality={quality_score:.2f}")

        return suggestion

    async def get_suggestions(
        self,
        db: AsyncSession,
        content_id: str,
    ) -> List[ReplySuggestion]:
        """
        获取内容的所有回复建议

        Args:
            db: 数据库会话
            content_id: 内容 ID

        Returns:
            回复建议列表
        """
        result = await db.execute(
            select(ReplySuggestion)
            .where(ReplySuggestion.content_id == content_id)
            .order_by(ReplySuggestion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
    ) -> Optional[ReplySuggestion]:
        """
        获取单个回复建议

        Args:
            db: 数据库会话
            suggestion_id: 建议 ID

        Returns:
            回复建议对象
        """
        result = await db.execute(
            select(ReplySuggestion).where(ReplySuggestion.id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def submit_feedback(
        self,
        db: AsyncSession,
        suggestion_id: str,
        feedback: str,
        edited_content: Optional[str] = None,
    ) -> ReplySuggestion:
        """
        提交用户反馈

        Args:
            db: 数据库会话
            suggestion_id: 建议 ID
            feedback: 反馈类型 (helpful, not_helpful, edited)
            edited_content: 编辑后的内容

        Returns:
            更新后的建议对象
        """
        suggestion = await self.get_suggestion(db, suggestion_id)
        if not suggestion:
            raise ValueError(f"建议不存在: {suggestion_id}")

        suggestion.user_feedback = feedback
        if edited_content:
            suggestion.edited_content = edited_content

        logger.info(f"提交反馈: suggestion_id={suggestion_id}, feedback={feedback}")
        return suggestion

    async def mark_published(
        self,
        db: AsyncSession,
        suggestion_id: str,
    ) -> ReplySuggestion:
        """
        标记为已发布

        Args:
            db: 数据库会话
            suggestion_id: 建议 ID

        Returns:
            更新后的建议对象
        """
        suggestion = await self.get_suggestion(db, suggestion_id)
        if not suggestion:
            raise ValueError(f"建议不存在: {suggestion_id}")

        suggestion.is_published = True
        suggestion.is_selected = True

        # 更新关联内容状态
        content = await self._get_content(db, suggestion.content_id)
        if content:
            content.status = ContentStatus.PUBLISHED

        logger.info(f"标记发布: suggestion_id={suggestion_id}")
        return suggestion

    def _build_reply_query(self, content: SocialContent, max_length: int) -> str:
        """构建用于 RAG 检索的查询"""
        parts = []

        # 内容类型
        type_names = {
            "question": "问题",
            "answer": "回答",
            "post": "帖子",
            "comment": "评论",
            "thread": "讨论",
        }
        type_name = type_names.get(content.content_type.value, "内容")

        if content.title:
            parts.append(f"{type_name}标题: {content.title}")

        parts.append(f"{type_name}内容: {content.content[:1000]}")

        # 添加分析结果作为上下文
        if content.analysis_result:
            topics = content.analysis_result.get("topics", [])
            if topics:
                parts.append(f"相关主题: {', '.join(topics)}")

            difficulty = content.analysis_result.get("difficulty_level")
            if difficulty:
                level_names = {
                    "beginner": "初学者",
                    "intermediate": "中级",
                    "advanced": "高级",
                }
                parts.append(f"适合水平: {level_names.get(difficulty, difficulty)}")

        parts.append(f"请提供专业的回复建议，回复长度控制在 {max_length} 字以内。")

        return "\n".join(parts)

    def _evaluate_reply_quality(
        self,
        question: str,
        reply: str,
    ) -> float:
        """
        评估回复质量

        基于多个维度评估回复质量:
        - 长度合适性
        - 关键词覆盖
        - 内容相关性
        """
        if len(reply) < 30:
            return 0.2

        score = 0.4  # 基础分

        # 长度评估
        if 100 <= len(reply) <= 600:
            score += 0.2
        elif 50 <= len(reply) < 100 or 600 < len(reply) <= 1000:
            score += 0.1

        # 乒乓球相关词汇覆盖
        keywords = [
            "乒乓球", "发球", "接发球", "旋转", "弧圈", "控制", "力量", "步法",
            "正手", "反手", "推挡", "削球", "拉球", "搓球", "击球", "落点",
            "底板", "胶皮", "海绵", "握拍", "站位", "挥拍", "技术", "训练",
        ]
        keyword_count = sum(1 for k in keywords if k in reply)
        score += min(keyword_count * 0.03, 0.2)

        # 结构性评估（有列表或分段）
        if any(marker in reply for marker in ["1.", "2.", "①", "②", "首先", "其次", "最后", "\n\n"]):
            score += 0.1

        # 具体性评估（有具体建议或数字）
        if any(char.isdigit() for char in reply):
            score += 0.05

        return min(score, 1.0)

    async def _get_content(
        self,
        db: AsyncSession,
        content_id: str,
    ) -> Optional[SocialContent]:
        """获取内容"""
        result = await db.execute(
            select(SocialContent)
            .options(selectinload(SocialContent.platform_config))
            .where(SocialContent.id == content_id)
        )
        return result.scalar_one_or_none()


# 工厂函数
def get_reply_service() -> ReplyService:
    """获取回复服务实例"""
    return ReplyService()
