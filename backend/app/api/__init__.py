"""api 层路由集合。

结构约定：6 组业务路由（auth/qa/chat/documents/search/kb）与 services 层的 6 个能力函数
一一对应；health 为独立的探活路由。
"""

from app.api import auth, chat, documents, health, kb, qa, search

__all__ = ["auth", "chat", "documents", "health", "kb", "qa", "search"]
