"""问答/助手/文档/搜索/知识库模块的请求与响应模型。

本轮为骨架批次，契约按技术方案 §三 固定，后续批次只往里填充实现。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QaAskRequest(BaseModel):
    """校园问答请求。"""

    question: str = Field(min_length=1, max_length=2000, description="学生提出的问题")
    session_id: int | None = Field(default=None, description="为空则新建会话")


class ChatSendRequest(BaseModel):
    """学习助手消息请求。"""

    content: str = Field(min_length=1, max_length=8000, description="消息正文")
    template: str | None = Field(default=None, description="free/plan/concept/hint")


class DocumentAskRequest(BaseModel):
    """文档问答请求。"""

    question: str = Field(min_length=1, max_length=2000, description="针对文档提出的问题")


class KbItemCreateRequest(BaseModel):
    """知识库条目录入请求（对应 T6 全字段）。"""

    question: str = Field(min_length=1, max_length=500, description="标准问法")
    aliases: list[str] = Field(default_factory=list, description="同义问法数组")
    answer: str = Field(default="", description="预期回答要点（Markdown）")
    answer_missing: str | None = Field(default=None, description="暂缺时的占位说明")
    category: str = Field(min_length=1, max_length=32, description="S1–S5 一级分类")
    subcategory: str | None = Field(default=None, max_length=64, description="二级分类")
    priority: str = Field(default="P2", pattern="^(P0|P1|P2)$")
    evidence: str = Field(default="E3", pattern="^(E1|E2|E3)$")
    evidence_source: str | None = Field(default=None, description="证据来源")
    status: str = Field(default="candidate", pattern="^(candidate|verified|published|retired)$")
    legacy_id: str | None = Field(default=None, description="语料库原 id，如 Q-S3-001")
    source_doc: str | None = Field(default=None, description="核对用的官方文件名称或 URL")


class KbItemUpdateRequest(BaseModel):
    """知识库条目修改请求；未提供的字段保持不变。"""

    question: str | None = Field(default=None, max_length=500)
    aliases: list[str] | None = None
    answer: str | None = None
    answer_missing: str | None = None
    category: str | None = Field(default=None, max_length=32)
    subcategory: str | None = Field(default=None, max_length=64)
    priority: str | None = Field(default=None, pattern="^(P0|P1|P2)$")
    evidence: str | None = Field(default=None, pattern="^(E1|E2|E3)$")
    evidence_source: str | None = None
    status: str | None = Field(default=None, pattern="^(candidate|verified|published|retired)$")
    legacy_id: str | None = Field(default=None)
    source_doc: str | None = None
