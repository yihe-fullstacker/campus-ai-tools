"""LLM Provider 抽象接口。

只定义两个最小操作：``chat``（对话生成）与 ``embed``（向量嵌入）。
业务层只依赖本模块的协议，具体厂商 SDK 只能出现在 ``providers/`` 目录内。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatMessage:
    """一条对话消息。"""

    role: str
    content: str


@dataclass(frozen=True)
class ChatResult:
    """一次对话生成的结果。"""

    text: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class LLMError(RuntimeError):
    """LLM 调用失败（未配置、鉴权失败、限流、网络异常、返回结构异常等）。"""


@runtime_checkable
class LLMProvider(Protocol):
    """统一的 Provider 抽象接口。"""

    name: str

    def chat(
        self, messages: Sequence[ChatMessage], options: dict[str, Any] | None = None
    ) -> ChatResult:
        """根据对话消息生成回复。"""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """把一批文本编码为向量。"""
        ...
