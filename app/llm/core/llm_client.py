"""
LLM 客户端模块
封装 OpenAI 兼容 API 的调用
"""

from typing import List, Optional, AsyncGenerator, Union
from functools import lru_cache
from openai import AsyncOpenAI
from loguru import logger

from config.settings import get_settings
from app.llm.schemas import ChatMessage


class LLMClient:
    """
    OpenAI 兼容 API 客户端
    支持任何兼容 OpenAI 格式的 API（OpenAI、OhMyGPT 等）
    """

    def __init__(self, api_key: str, base_url: str):
        """
        初始化客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.base_url = base_url
        logger.info(f"LLM 客户端已初始化，API 地址: {base_url}")

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        聊天补全接口

        Args:
            messages: 消息历史
            model: 模型名称
            temperature: 生成温度
            max_tokens: 最大 token 数
            stream: 是否流式输出

        Returns:
            非流式: 响应文本
            流式: 异步生成器
        """
        # 转换消息格式
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        logger.debug(f"调用 LLM，模型: {model}，消息数: {len(messages)}")

        if stream:
            return self._stream_completion(
                formatted_messages, model, temperature, max_tokens
            )
        else:
            return await self._regular_completion(
                formatted_messages, model, temperature, max_tokens
            )

    async def _regular_completion(
        self,
        messages: List[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """非流式补全"""
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            logger.debug(f"LLM 响应完成，tokens: {tokens_used}")
            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def _stream_completion(
        self,
        messages: List[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """流式补全"""
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise

    async def chat_completion_with_tokens(
        self,
        messages: List[ChatMessage],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> tuple[str, Optional[int]]:
        """
        聊天补全，返回内容和 token 使用量

        Args:
            messages: 消息历史
            model: 模型名称
            temperature: 生成温度
            max_tokens: 最大 token 数

        Returns:
            (响应文本, token 使用量)
        """
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None
            return content, tokens_used
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise


# 单例实例
_llm_client: Optional[LLMClient] = None


@lru_cache
def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        settings = get_settings()
        _llm_client = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _llm_client
