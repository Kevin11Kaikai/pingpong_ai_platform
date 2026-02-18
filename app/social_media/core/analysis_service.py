"""
内容分析服务
使用 LLM 分析社交媒体内容，提取主题、情感、关键点
"""

from typing import List, Optional, Tuple
import uuid
import json
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.social_media.models import (
    SocialContent, ContentTag, ContentTagMapping, ContentStatus
)
from app.shared.embedding_service import EmbeddingService
from app.llm.core.llm_client import get_llm_client, LLMClient
from app.llm.schemas import ChatMessage


@dataclass
class AnalysisResult:
    """分析结果"""
    topics: List[str]
    question_type: Optional[str]
    difficulty_level: Optional[str]
    sentiment: str
    key_points: List[str]
    suggested_tags: List[str]
    quality_score: float
    relevance_score: float


# 分析提示模板
ANALYSIS_PROMPT = """请分析以下乒乓球相关的社交媒体内容，提取关键信息。

内容类型: {content_type}
标题: {title}
内容:
---
{content}
---

请以 JSON 格式返回分析结果：
{{
    "topics": ["主题1", "主题2"],
    "question_type": "technique|equipment|rule|training|other|null",
    "difficulty_level": "beginner|intermediate|advanced|null",
    "sentiment": "positive|neutral|negative",
    "key_points": ["要点1", "要点2"],
    "suggested_tags": ["标签1", "标签2"],
    "quality_score": 0.0-1.0,
    "relevance_score": 0.0-1.0
}}

说明:
- topics: 涉及的乒乓球话题，如"正手技术"、"发球"、"装备选择"等
- question_type: 问题类型，technique=技术问题，equipment=装备问题，rule=规则问题，training=训练问题
- difficulty_level: 内容适合的水平，beginner=初学者，intermediate=中级，advanced=高级
- sentiment: 情感倾向
- key_points: 提取的关键信息点
- suggested_tags: 建议的标签
- quality_score: 内容质量评分(0-1)，考虑内容的完整性、准确性、可读性
- relevance_score: 与乒乓球的相关度(0-1)

只返回 JSON，不要其他内容。"""


class AnalysisService:
    """
    内容分析服务
    使用 LLM 进行内容理解和信息提取
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or get_llm_client()

    async def analyze_content(
        self,
        db: AsyncSession,
        content_id: str,
        force_reanalyze: bool = False,
    ) -> AnalysisResult:
        """
        分析单个内容

        Args:
            db: 数据库会话
            content_id: 内容 ID
            force_reanalyze: 是否强制重新分析

        Returns:
            分析结果
        """
        # 获取内容
        content = await self._get_content(db, content_id)
        if not content:
            raise ValueError(f"内容不存在: {content_id}")

        # 检查是否已分析
        if content.analysis_result and not force_reanalyze:
            return self._parse_stored_result(content.analysis_result)

        # 构建分析文本
        text_to_analyze = content.content[:2000]  # 限制长度

        # 调用 LLM 分析
        result = await self._call_llm_analysis(
            content_type=content.content_type.value,
            title=content.title or "",
            content=text_to_analyze,
        )

        # 生成嵌入向量（如果还没有）
        if not content.embedding:
            text = f"{content.title or ''} {content.content}"
            content.embedding = EmbeddingService.encode_single(text).tolist()

        # 更新内容记录
        content.analysis_result = {
            "topics": result.topics,
            "question_type": result.question_type,
            "difficulty_level": result.difficulty_level,
            "sentiment": result.sentiment,
            "key_points": result.key_points,
            "suggested_tags": result.suggested_tags,
        }
        content.quality_score = result.quality_score
        content.relevance_score = result.relevance_score
        content.status = ContentStatus.ANALYZED

        # 自动添加标签
        await self._auto_tag_content(db, content, result.suggested_tags)

        logger.info(f"内容分析完成: {content_id}, 质量分: {result.quality_score:.2f}")

        return result

    async def batch_analyze(
        self,
        db: AsyncSession,
        content_ids: Optional[List[str]] = None,
        status_filter: Optional[ContentStatus] = ContentStatus.PENDING,
        limit: int = 50,
    ) -> Tuple[int, int]:
        """
        批量分析内容

        Args:
            db: 数据库会话
            content_ids: 指定的内容 ID 列表
            status_filter: 状态筛选
            limit: 处理数量限制

        Returns:
            (成功数, 失败数)
        """
        # 获取待分析内容
        if content_ids:
            contents = await self._get_contents_by_ids(db, content_ids)
        else:
            contents = await self._get_contents_by_status(db, status_filter, limit)

        success_count = 0
        fail_count = 0

        for content in contents:
            try:
                await self.analyze_content(db, content.id)
                success_count += 1
            except Exception as e:
                logger.error(f"分析失败 {content.id}: {e}")
                fail_count += 1

        logger.info(f"批量分析完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count, fail_count

    async def _call_llm_analysis(
        self,
        content_type: str,
        title: str,
        content: str,
    ) -> AnalysisResult:
        """调用 LLM 进行分析"""
        prompt = ANALYSIS_PROMPT.format(
            content_type=content_type,
            title=title or "(无标题)",
            content=content,
        )

        messages = [
            ChatMessage(role="user", content=prompt)
        ]

        response = await self.llm_client.chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.3,  # 低温度确保一致性
        )

        # 解析 JSON 响应
        try:
            # 尝试提取 JSON 部分
            response_text = response.strip()
            if response_text.startswith("```"):
                # 去掉 markdown 代码块
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])

            data = json.loads(response_text)
            return AnalysisResult(
                topics=data.get("topics", []),
                question_type=data.get("question_type"),
                difficulty_level=data.get("difficulty_level"),
                sentiment=data.get("sentiment", "neutral"),
                key_points=data.get("key_points", []),
                suggested_tags=data.get("suggested_tags", []),
                quality_score=float(data.get("quality_score", 0.5)),
                relevance_score=float(data.get("relevance_score", 0.5)),
            )
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"解析 LLM 响应失败: {e}, 响应: {response[:200]}")
            # 返回默认结果
            return AnalysisResult(
                topics=[],
                question_type=None,
                difficulty_level=None,
                sentiment="neutral",
                key_points=[],
                suggested_tags=[],
                quality_score=0.5,
                relevance_score=0.5,
            )

    def _parse_stored_result(self, stored: dict) -> AnalysisResult:
        """解析存储的分析结果"""
        return AnalysisResult(
            topics=stored.get("topics", []),
            question_type=stored.get("question_type"),
            difficulty_level=stored.get("difficulty_level"),
            sentiment=stored.get("sentiment", "neutral"),
            key_points=stored.get("key_points", []),
            suggested_tags=stored.get("suggested_tags", []),
            quality_score=stored.get("quality_score", 0.5),
            relevance_score=stored.get("relevance_score", 0.5),
        )

    async def _auto_tag_content(
        self,
        db: AsyncSession,
        content: SocialContent,
        suggested_tags: List[str],
    ) -> None:
        """自动为内容添加标签"""
        for tag_name in suggested_tags[:5]:  # 最多添加5个标签
            # 获取或创建标签
            tag = await self._get_or_create_tag(db, tag_name)

            # 检查是否已关联
            existing = await db.execute(
                select(ContentTagMapping).where(
                    ContentTagMapping.content_id == content.id,
                    ContentTagMapping.tag_id == tag.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # 创建关联
            mapping = ContentTagMapping(
                id=str(uuid.uuid4()),
                content_id=content.id,
                tag_id=tag.id,
                source="ai",
                confidence=0.8,
            )
            db.add(mapping)

            # 更新标签使用次数
            tag.usage_count += 1

    async def _get_or_create_tag(
        self,
        db: AsyncSession,
        tag_name: str,
    ) -> ContentTag:
        """获取或创建标签"""
        # 标准化标签名
        normalized_name = tag_name.strip().lower()

        result = await db.execute(
            select(ContentTag).where(ContentTag.name == normalized_name)
        )
        tag = result.scalar_one_or_none()

        if not tag:
            tag = ContentTag(
                id=str(uuid.uuid4()),
                name=normalized_name,
                display_name=tag_name.strip(),
            )
            db.add(tag)
            await db.flush()

        return tag

    async def _get_content(
        self,
        db: AsyncSession,
        content_id: str,
    ) -> Optional[SocialContent]:
        """获取内容"""
        result = await db.execute(
            select(SocialContent).where(SocialContent.id == content_id)
        )
        return result.scalar_one_or_none()

    async def _get_contents_by_ids(
        self,
        db: AsyncSession,
        content_ids: List[str],
    ) -> List[SocialContent]:
        """根据 ID 列表获取内容"""
        result = await db.execute(
            select(SocialContent).where(SocialContent.id.in_(content_ids))
        )
        return list(result.scalars().all())

    async def _get_contents_by_status(
        self,
        db: AsyncSession,
        status: Optional[ContentStatus],
        limit: int,
    ) -> List[SocialContent]:
        """根据状态获取内容"""
        query = select(SocialContent)
        if status:
            query = query.where(SocialContent.status == status)
        query = query.order_by(SocialContent.created_at.asc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


# 工厂函数
def get_analysis_service() -> AnalysisService:
    """获取分析服务实例"""
    return AnalysisService()
