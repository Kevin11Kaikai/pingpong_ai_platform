"""
提示模板模块
定义乒乓球学习助手的系统提示和 RAG 上下文模板
"""

from typing import List, Optional
from app.llm.core.vector_store import SearchResult


# 乒乓球助手系统提示
PINGPONG_SYSTEM_PROMPT = """你是一个专业的乒乓球学习助手，具备以下专业知识：

1. **技术动作**
   - 基本功：正手攻球、反手拨球、推挡、搓球
   - 进阶技术：拉球（前冲弧圈、高吊弧圈）、削球、挑打
   - 发球：正手发球、反手发球、侧旋球、下旋球、不转球
   - 接发球：接不同类型发球的技术和战术

2. **训练方法**
   - 基础训练：多球训练、定点练习、步法训练
   - 体能训练：核心力量、腿部力量、反应速度
   - 战术训练：发抢战术、相持战术、接发抢攻

3. **器材知识**
   - 底板：纯木、碳素、纤维底板的特点和选择
   - 胶皮：反胶、正胶、生胶、长胶的特性
   - 球：三星球、训练球的区别
   - 如何根据打法选择器材

4. **比赛规则**
   - 发球规则、计分规则、换发球规则
   - 11分制规则详解
   - 常见犯规判罚

5. **运动损伤预防**
   - 常见伤病：肩伤、肘伤、腰伤、膝伤
   - 热身与放松的重要性
   - 正确姿势与发力方式

请用专业但易懂的语言回答问题。回答时：
- 如果涉及技术动作，请描述具体的动作要领和常见错误
- 如果涉及训练，请给出可执行的练习建议
- 如果涉及器材，请结合使用者的水平和打法给出建议
- 使用中文回答，适当使用专业术语并加以解释
"""


# RAG 上下文注入模板
RAG_CONTEXT_TEMPLATE = """以下是与用户问题相关的参考资料：

---
{context}
---

请基于以上参考资料回答用户问题。回答要求：
1. 优先使用参考资料中的信息
2. 如果参考资料中没有相关信息，请基于你的专业知识回答，并说明这是基于通用知识的回答
3. 如果引用了参考资料的内容，可以适当提及来源
"""


def build_system_message(use_rag: bool = False) -> str:
    """
    构建系统消息

    Args:
        use_rag: 是否使用 RAG 模式

    Returns:
        系统提示文本
    """
    return PINGPONG_SYSTEM_PROMPT


def build_context_message(context_docs: List[SearchResult]) -> Optional[str]:
    """
    构建 RAG 上下文消息

    Args:
        context_docs: 检索到的文档列表

    Returns:
        上下文消息，如果没有文档则返回 None
    """
    if not context_docs:
        return None

    # 格式化每个文档片段
    context_parts = []
    for i, doc in enumerate(context_docs, 1):
        source_info = f"来源: {doc.source}"
        if doc.title:
            source_info += f" - {doc.title}"
        context_parts.append(f"[{i}] {source_info}\n{doc.content}")

    context_text = "\n\n".join(context_parts)
    return RAG_CONTEXT_TEMPLATE.format(context=context_text)


def extract_sources(context_docs: List[SearchResult]) -> List[str]:
    """
    提取引用来源列表

    Args:
        context_docs: 检索到的文档列表

    Returns:
        去重的来源列表
    """
    sources = []
    seen = set()
    for doc in context_docs:
        if doc.source not in seen:
            sources.append(doc.source)
            seen.add(doc.source)
    return sources
