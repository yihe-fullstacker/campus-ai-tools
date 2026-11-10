"""问答/助手/文档/搜索/知识库模块的请求与响应模型。

本轮为骨架批次，契约按技术方案 §三 固定，后续批次只往里填充实现。

跨字段约束：``status=verified`` 表示"已核对本校官方资料"，因此必须同时具备 E1/E2 证据；
E3 候选条目不得标记为已核实（E3 只作未核实通用建议，命中时返回 ``verified: false``）。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

VERIFIED_EVIDENCE = ("E1", "E2")
VERIFIED_REQUIRES_OFFICIAL_EVIDENCE = (
    "status=verified 要求 evidence 为 E1 或 E2；E3 候选条目不得标记为已核实"
)


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

    @model_validator(mode="after")
    def check_verified_evidence(self) -> KbItemCreateRequest:
        """已核实状态必须搭配 E1/E2 证据。"""
        if self.status == "verified" and self.evidence not in VERIFIED_EVIDENCE:
            raise ValueError(VERIFIED_REQUIRES_OFFICIAL_EVIDENCE)
        return self


class KbItemUpdateRequest(BaseModel):
    """知识库条目修改请求；未提供的字段保持不变。

    注意：仅当请求同时给出 ``status`` 与 ``evidence`` 时才能在本地完成跨字段校验；
    只改 ``status`` 的场景需由服务层与库中现值合并后再校验（后续批次实现）。
    """

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
    legacy_id: str | None = None
    source_doc: str | None = None

    @model_validator(mode="after")
    def check_verified_evidence(self) -> KbItemUpdateRequest:
        """已核实状态不得搭配 E3 证据。"""
        if (
            self.status == "verified"
            and self.evidence is not None
            and self.evidence not in VERIFIED_EVIDENCE
        ):
            raise ValueError(VERIFIED_REQUIRES_OFFICIAL_EVIDENCE)
        return self
