"""LLM Provider 层。

业务代码只依赖 ``LLMProvider`` 协议，不 import 任何厂商 SDK；
新增或切换 Provider 只需在 ``providers/`` 下新增实现文件并修改配置。
"""

from __future__ import annotations

from app.services.llm.base import ChatMessage, ChatResult, LLMError, LLMProvider
from app.services.llm.providers.deepseek import DeepSeekProvider

__all__ = [
    "ChatMessage",
    "ChatResult",
    "DeepSeekProvider",
    "LLMError",
    "LLMProvider",
    "get_provider",
]


def get_provider(name: str | None = None) -> LLMProvider:
    """按配置（默认取 ``LLM_PROVIDER``）返回 Provider 实现。"""
    from app.config import get_settings

    provider_name = (name or get_settings().llm_provider).strip().lower()
    if provider_name == "deepseek":
        return DeepSeekProvider()
    raise LLMError(f"未知的 LLM Provider：{provider_name}")
