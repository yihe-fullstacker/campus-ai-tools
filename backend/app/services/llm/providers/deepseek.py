"""DeepSeek Provider 实现（OpenAI 兼容接口）。

依赖 httpx 直接调用 HTTP 接口，避免把厂商 SDK 泄漏到业务层。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from app.config import get_settings
from app.services.llm.base import ChatMessage, ChatResult, LLMError

DEFAULT_TIMEOUT_SECONDS = 60.0
ERROR_TEXT_LIMIT = 200


class DeepSeekProvider:
    """DeepSeek 的 Provider 实现。"""

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.deepseek_api_key
        self.base_url = (base_url or settings.deepseek_base_url).rstrip("/")
        self.model = model or settings.deepseek_model
        self.embedding_model = embedding_model or settings.deepseek_embedding_model

    def chat(
        self, messages: Sequence[ChatMessage], options: dict[str, Any] | None = None
    ) -> ChatResult:
        """调用 ``/chat/completions`` 生成回复。"""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
        }
        if options:
            payload.update(options)
        data = self._post("/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("DeepSeek 返回结构异常，无法解析回答内容。") from exc
        usage_raw = data.get("usage") or {}
        usage = {key: int(value) for key, value in usage_raw.items() if isinstance(value, int)}
        return ChatResult(text=text, model=str(data.get("model") or self.model), usage=usage)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """调用 ``/embeddings`` 生成向量。"""
        if not texts:
            return []
        data = self._post("/embeddings", {"model": self.embedding_model, "input": list(texts)})
        items = data.get("data") or []
        if not isinstance(items, list):
            raise LLMError("DeepSeek 返回结构异常，无法解析向量结果。")
        ordered = sorted(items, key=lambda item: item.get("index", 0))
        try:
            return [item["embedding"] for item in ordered]
        except (KeyError, TypeError) as exc:
            raise LLMError("DeepSeek 返回结构异常，无法解析向量结果。") from exc

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """发起一次 POST 请求，返回解析后的 JSON。"""
        if not self.api_key:
            raise LLMError("未配置 DEEPSEEK_API_KEY，无法调用大模型服务。")
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"调用 DeepSeek 接口失败：{exc}") from exc
        if response.status_code != 200:
            raise LLMError(
                f"DeepSeek 接口返回 {response.status_code}：{response.text[:ERROR_TEXT_LIMIT]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("DeepSeek 接口返回的不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise LLMError("DeepSeek 接口返回的不是 JSON 对象。")
        return data
