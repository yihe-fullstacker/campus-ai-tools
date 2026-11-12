"""用户自助模型配置接口（BYOK）。

接口只返回密钥掩码，任何情况下都不回传明文。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_db
from app.services import llm_config_service

router = APIRouter(prefix="/llm-configs", tags=["llm-configs"])


class LlmConfigCreateRequest(BaseModel):
    """新增模型配置。"""

    provider: str = Field(default="openai-compatible", max_length=64)
    display_name: str | None = Field(default=None, max_length=80)
    base_url: str | None = Field(default=None, max_length=300)
    model: str = Field(min_length=1, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    api_key: str = Field(min_length=1, max_length=512)


class LlmConfigUpdateRequest(BaseModel):
    """修改模型配置；api_key 留空表示沿用原密钥。"""

    provider: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=80)
    base_url: str | None = Field(default=None, max_length=300)
    model: str | None = Field(default=None, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    api_key: str | None = Field(default=None, max_length=512)


class LlmConfigTestRequest(BaseModel):
    """测试配置；给出 api_key 时测试未保存的草稿。"""

    config_id: int | None = None
    provider: str | None = Field(default=None, max_length=64)
    base_url: str | None = Field(default=None, max_length=300)
    model: str | None = Field(default=None, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    api_key: str | None = Field(default=None, max_length=512)


@router.get("/presets", summary="常见国产模型厂商预设")
def list_presets() -> list[dict]:
    """返回厂商预设，前端据此生成下拉与占位提示。"""
    return llm_config_service.list_presets()


@router.get("", summary="我的模型配置列表")
def list_configs(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """列出当前用户的模型配置（密钥仅显示掩码）。"""
    return llm_config_service.list_configs(conn, user["id"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="新增模型配置")
def create_config(
    payload: LlmConfigCreateRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """保存一份新的模型配置；首个配置自动生效。"""
    return llm_config_service.create_config(conn, user["id"], payload.model_dump())


@router.put("/{config_id}", summary="修改模型配置")
def update_config(
    config_id: int,
    payload: LlmConfigUpdateRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """修改配置；不填 api_key 表示沿用原密钥。"""
    return llm_config_service.update_config(
        conn, user["id"], config_id, payload.model_dump(exclude_unset=True)
    )


@router.post("/{config_id}/activate", summary="设为当前生效配置")
def activate_config(
    config_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """把指定配置设为当前生效。"""
    return llm_config_service.activate_config(conn, user["id"], config_id)


@router.delete("/{config_id}", summary="删除模型配置")
def delete_config(
    config_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """删除配置。"""
    return llm_config_service.delete_config(conn, user["id"], config_id)


@router.post("/test", summary="连通性测试")
def test_config(
    payload: LlmConfigTestRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """用一次极短对话验证密钥与接口是否可用。"""
    draft = payload.model_dump(exclude={"config_id"})
    has_draft_key = bool(draft.get("api_key"))
    return llm_config_service.test_config(
        conn,
        user["id"],
        config_id=None if has_draft_key else payload.config_id,
        payload=draft if has_draft_key else None,
    )
