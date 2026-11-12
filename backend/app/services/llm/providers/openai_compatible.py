"""OpenAI 兼容协议的通用 Provider。

国内主流大模型（DeepSeek、通义千问、智谱 GLM、Kimi 月之暗面、豆包方舟、
MiniMax、百川、阶跃星辰等）以及 Ollama / vLLM 自建服务，
大多提供 OpenAI 兼容的 ``/chat/completions`` 与 ``/embeddings`` 接口，
因此统一由本 Provider 承载：用户只需填写 base_url、模型名和密钥。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from app.services.llm.base import ChatMessage, ChatResult, LLMError

DEFAULT_TIMEOUT_SECONDS = 60.0
ERROR_TEXT_LIMIT = 300


class OpenAICompatibleProvider:
    """按 OpenAI 兼容协议访问任意厂商。"""

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        embedding_model: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.embedding_model = embedding_model or ""
        self.timeout_seconds = timeout_seconds
        self.extra_headers = extra_headers or {}

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def chat(
        self, messages: Sequence[ChatMessage], options: dict[str, Any] | None = None
    ) -> ChatResult:
        """调用 ``/chat/completions`` 生成回复。"""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if options:
            payload.update(options)
        data = self._post("/chat/completions", payload)
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("模型接口返回结构异常，无法解析回答内容。") from exc
        if not isinstance(text, str):
            raise LLMError("模型接口返回的回答内容不是文本。")
        usage_raw = data.get("usage") or {}
        usage = {k: int(v) for k, v in usage_raw.items() if isinstance(v, int)}
        return ChatResult(text=text, model=str(data.get("model") or self.model), usage=usage)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """调用 ``/embeddings`` 生成向量。"""
        if not texts:
            return []
        if not self.embedding_model:
            raise LLMError("未配置向量模型，无法生成向量。")
        data = self._post("/embeddings", {"model": self.embedding_model, "input": list(texts)})
        items = data.get("data") or []
        if not isinstance(items, list):
            raise LLMError("模型接口返回结构异常，无法解析向量结果。")
        ordered = sorted(items, key=lambda item: item.get("index", 0))
        try:
            return [item["embedding"] for item in ordered]
        except (KeyError, TypeError) as exc:
            raise LLMError("模型接口返回结构异常，无法解析向量结果。") from exc

    def list_models(self) -> list[str]:
        """尝试读取 ``/models``；不支持时返回空列表。"""
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError:
            return []
        if response.status_code != 200:
            return []
        try:
            data = response.json()
        except ValueError:
            return []
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return [str(item["id"]) for item in items if isinstance(item, dict) and "id" in item]

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """发起一次 POST 请求并解析 JSON。"""
        if not self.api_key:
            raise LLMError("未配置 API 密钥，无法调用模型服务。")
        if not self.base_url:
            raise LLMError("未配置接口地址，无法调用模型服务。")
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise LLMError("模型接口响应超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"调用模型接口失败：{exc}") from exc

        if response.status_code == 401:
            raise LLMError("API 密钥无效或已过期，请检查后重新填写。")
        if response.status_code == 402:
            raise LLMError("账户额度不足，请前往模型厂商控制台充值。")
        if response.status_code == 429:
            raise LLMError("调用过于频繁或已超出额度限制，请稍后重试。")
        if response.status_code != 200:
            raise LLMError(
                f"模型接口返回 {response.status_code}：{response.text[:ERROR_TEXT_LIMIT]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("模型接口返回的不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise LLMError("模型接口返回的不是 JSON 对象。")
        return data
