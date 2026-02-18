"""
对话服务模块
处理会话创建、历史管理、消息存储
"""

import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.llm.models import Conversation, Message
from app.llm.schemas import ChatMessage


class ConversationService:
    """
    对话管理服务
    处理会话创建、历史管理、消息存储
    """

    def __init__(self, db_session: AsyncSession):
        """
        初始化服务

        Args:
            db_session: 异步数据库会话
        """
        self.db = db_session

    async def create_conversation(
        self,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        """
        创建新会话

        Args:
            user_id: 可选用户 ID
            title: 可选会话标题

        Returns:
            创建的会话对象
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(conversation)
        await self.db.flush()
        logger.info(f"创建会话: {conversation.id}")
        return conversation

    async def get_conversation(
        self,
        conversation_id: str,
    ) -> Optional[Conversation]:
        """
        获取会话详情

        Args:
            conversation_id: 会话 ID

        Returns:
            会话对象，不存在则返回 None
        """
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Conversation], int]:
        """
        列出用户会话

        Args:
            user_id: 可选用户 ID 过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (会话列表, 总数)
        """
        # 构建查询
        query = select(Conversation)
        count_query = select(func.count(Conversation.id))

        if user_id:
            query = query.where(Conversation.user_id == user_id)
            count_query = count_query.where(Conversation.user_id == user_id)

        # 获取总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 获取列表
        query = query.order_by(Conversation.updated_at.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        conversations = list(result.scalars().all())

        return conversations, total

    async def delete_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        """
        删除会话

        Args:
            conversation_id: 会话 ID

        Returns:
            是否删除成功
        """
        result = await self.db.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除会话: {conversation_id}")
        return deleted

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tokens_used: Optional[int] = None,
    ) -> Message:
        """
        添加消息到会话

        Args:
            conversation_id: 会话 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            tokens_used: 使用的 token 数

        Returns:
            创建的消息对象
        """
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            created_at=datetime.utcnow(),
        )
        self.db.add(message)

        # 更新会话的更新时间
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.updated_at = datetime.utcnow()

        await self.db.flush()
        logger.debug(f"添加消息到会话 {conversation_id}: {role}")
        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Message]:
        """
        获取会话消息历史

        Args:
            conversation_id: 会话 ID
            limit: 返回数量限制

        Returns:
            消息列表（按时间正序）
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_message_count(
        self,
        conversation_id: str,
    ) -> int:
        """
        获取会话消息数量

        Args:
            conversation_id: 会话 ID

        Returns:
            消息数量
        """
        result = await self.db.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar() or 0

    async def update_title(
        self,
        conversation_id: str,
        title: str,
    ) -> Optional[Conversation]:
        """
        更新会话标题

        Args:
            conversation_id: 会话 ID
            title: 新标题

        Returns:
            更新后的会话，不存在则返回 None
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.title = title
            conversation.updated_at = datetime.utcnow()
            await self.db.flush()
            logger.info(f"更新会话标题: {conversation_id} -> {title}")
        return conversation

    async def get_chat_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[ChatMessage]:
        """
        获取聊天历史（转换为 ChatMessage 格式）

        Args:
            conversation_id: 会话 ID
            limit: 返回数量限制

        Returns:
            ChatMessage 列表
        """
        messages = await self.get_messages(conversation_id, limit)
        return [
            ChatMessage(role=msg.role, content=msg.content)
            for msg in messages
        ]
