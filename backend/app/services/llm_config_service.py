"""用户自带大模型 API 配置（BYOK）。

用户在前端粘贴自己的 API 密钥，选择或自定义厂商与模型，用自己的额度调用。
安全约定：
- 密钥落库前加密，接口任何响应都不返回明文，只返回掩码；
- 配置仅在服务端解密使用，不写入日志；
- 用户可保存多份配置，同一时刻只有一份生效。
"""

from __future__ import annotations

import sqlite3

from app.errors import ApiError
from app.services.llm import base as llm_base
from app.services.llm.crypto import decrypt_secret, encrypt_secret, mask_key
from app.services.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.storage.db import utc_now_iso

MAX_CONFIGS_PER_USER = 10
MIN_KEY_LENGTH = 8
MAX_KEY_LENGTH = 512

# 常见国产模型厂商预设；用户仍可完全自定义 base_url 与模型名
PROVIDER_PRESETS: tuple[dict, ...] = (
    {
        "provider": "deepseek",
        "display_name": "DeepSeek 深度求索",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "embedding_model": "",
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "provider": "qwen",
        "display_name": "通义千问（阿里云百炼）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-max", "qwen-turbo"],
        "embedding_model": "text-embedding-v3",
        "docs_url": "https://bailian.console.aliyun.com/",
    },
    {
        "provider": "zhipu",
        "display_name": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4-flash", "glm-4-air"],
        "embedding_model": "embedding-3",
        "docs_url": "https://bigmodel.cn/usercenter/apikeys",
    },
    {
        "provider": "moonshot",
        "display_name": "Kimi 月之暗面",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "embedding_model": "",
        "docs_url": "https://platform.moonshot.cn/console/api-keys",
    },
    {
        "provider": "doubao",
        "display_name": "豆包（火山方舟）",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-pro-32k", "doubao-lite-32k"],
        "embedding_model": "",
        "docs_url": "https://console.volcengine.com/ark",
    },
    {
        "provider": "baichuan",
        "display_name": "百川智能",
        "base_url": "https://api.baichuan-ai.com/v1",
        "models": ["Baichuan4", "Baichuan3-Turbo"],
        "embedding_model": "",
        "docs_url": "https://platform.baichuan-ai.com/",
    },
    {
        "provider": "minimax",
        "display_name": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "models": ["abab6.5s-chat", "abab6.5g-chat"],
        "embedding_model": "",
        "docs_url": "https://platform.minimaxi.com/",
    },
    {
        "provider": "openai-compatible",
        "display_name": "自定义（OpenAI 兼容接口 / 本地 Ollama）",
        "base_url": "",
        "models": [],
        "embedding_model": "",
        "docs_url": "",
    },
)
KNOWN_PROVIDERS = {preset["provider"] for preset in PROVIDER_PRESETS}


def list_presets() -> list[dict]:
    """返回前端展示用的厂商预设列表。"""
    return [dict(preset) for preset in PROVIDER_PRESETS]


def _validate_payload(payload: dict, require_key: bool = True) -> dict:
    """校验并规整配置载荷。"""
    provider = (payload.get("provider") or "openai-compatible").strip()
    if provider not in KNOWN_PROVIDERS:
        raise ApiError(
            400,
            "LLM_PROVIDER_UNKNOWN",
            f"未知的模型厂商：{provider}；如需接入其他厂商请选择「自定义」。",
        )
    base_url = (payload.get("base_url") or "").strip()
    if not base_url:
        preset = next(p for p in PROVIDER_PRESETS if p["provider"] == provider)
        base_url = preset["base_url"]
    if not base_url:
        raise ApiError(400, "LLM_BASE_URL_REQUIRED", "请填写接口地址（base_url）。")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ApiError(400, "LLM_BASE_URL_INVALID", "接口地址需以 http:// 或 https:// 开头。")

    model = (payload.get("model") or "").strip()
    if not model:
        raise ApiError(400, "LLM_MODEL_REQUIRED", "请填写要使用的模型名称。")

    api_key = (payload.get("api_key") or "").strip()
    if require_key:
        if len(api_key) < MIN_KEY_LENGTH:
            raise ApiError(400, "LLM_API_KEY_INVALID", "API 密钥过短，请检查是否粘贴完整。")
        if len(api_key) > MAX_KEY_LENGTH:
            raise ApiError(400, "LLM_API_KEY_INVALID", "API 密钥过长，请检查粘贴内容。")

    display_name = (payload.get("display_name") or "").strip()
    if not display_name:
        preset = next(p for p in PROVIDER_PRESETS if p["provider"] == provider)
        display_name = f"{preset['display_name']} · {model}"

    return {
        "provider": provider,
        "display_name": display_name[:80],
        "base_url": base_url.rstrip("/"),
        "model": model[:120],
        "embedding_model": (payload.get("embedding_model") or "").strip()[:120] or None,
        "api_key": api_key,
    }


def _row_to_public(row: sqlite3.Row) -> dict:
    """转换为对外可见的配置（绝不包含明文密钥）。"""
    return {
        "id": row["id"],
        "provider": row["provider"],
        "display_name": row["display_name"],
        "base_url": row["base_url"],
        "model": row["model"],
        "embedding_model": row["embedding_model"],
        "api_key_hint": row["api_key_hint"],
        "is_active": bool(row["is_active"]),
        "last_verified_at": row["last_verified_at"],
        "last_error": row["last_error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_configs(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的模型配置。"""
    rows = conn.execute(
        """SELECT * FROM user_llm_configs WHERE user_id = ?
           ORDER BY is_active DESC, id DESC""",
        (user_id,),
    ).fetchall()
    return [_row_to_public(row) for row in rows]


def _get_row(conn: sqlite3.Connection, user_id: int, config_id: int) -> sqlite3.Row:
    """取出属于当前用户的配置。"""
    row = conn.execute(
        "SELECT * FROM user_llm_configs WHERE id = ? AND user_id = ?",
        (config_id, user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "LLM_CONFIG_NOT_FOUND", "模型配置不存在或不属于当前用户。")
    return row


def create_config(conn: sqlite3.Connection, user_id: int, payload: dict) -> dict:
    """新增一份模型配置；首个配置自动生效。"""
    count = int(
        conn.execute(
            "SELECT COUNT(*) FROM user_llm_configs WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    )
    if count >= MAX_CONFIGS_PER_USER:
        raise ApiError(
            400,
            "LLM_CONFIG_LIMIT",
            f"最多可保存 {MAX_CONFIGS_PER_USER} 份模型配置，请先删除不用的配置。",
        )

    data = _validate_payload(payload)
    now = utc_now_iso()
    is_active = 1 if count == 0 else 0
    conn.execute(
        """INSERT INTO user_llm_configs
           (user_id, provider, display_name, base_url, model, embedding_model,
            api_key_cipher, api_key_hint, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            data["provider"],
            data["display_name"],
            data["base_url"],
            data["model"],
            data["embedding_model"],
            encrypt_secret(data["api_key"]),
            mask_key(data["api_key"]),
            is_active,
            now,
            now,
        ),
    )
    config_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    return _row_to_public(_get_row(conn, user_id, config_id))


def update_config(
    conn: sqlite3.Connection, user_id: int, config_id: int, payload: dict
) -> dict:
    """修改配置；未提供 api_key 时沿用原密钥。"""
    row = _get_row(conn, user_id, config_id)
    # 与库中现值合并：只改部分字段时，其余字段沿用原配置
    merged = {
        "provider": row["provider"],
        "display_name": row["display_name"],
        "base_url": row["base_url"],
        "model": row["model"],
        "embedding_model": row["embedding_model"],
    }
    for key in ("provider", "display_name", "base_url", "model", "embedding_model"):
        value = payload.get(key)
        if value is not None:
            merged[key] = value
    new_key = (payload.get("api_key") or "").strip()
    if new_key:
        merged["api_key"] = new_key
        data = _validate_payload(merged)
    else:
        data = _validate_payload({**merged, "api_key": "placeholder-key"}, require_key=False)
        data.pop("api_key", None)

    now = utc_now_iso()
    assignments = [
        "provider = ?",
        "display_name = ?",
        "base_url = ?",
        "model = ?",
        "embedding_model = ?",
        "updated_at = ?",
    ]
    values: list[object] = [
        data["provider"],
        data["display_name"],
        data["base_url"],
        data["model"],
        data["embedding_model"],
        now,
    ]
    if "api_key" in data:
        assignments.extend(["api_key_cipher = ?", "api_key_hint = ?", "last_verified_at = NULL"])
        values.extend([encrypt_secret(data["api_key"]), mask_key(data["api_key"])])
    values.extend([config_id, user_id])

    conn.execute(
        f"UPDATE user_llm_configs SET {', '.join(assignments)} WHERE id = ? AND user_id = ?",
        values,
    )
    conn.commit()
    return _row_to_public(_get_row(conn, user_id, config_id))


def activate_config(conn: sqlite3.Connection, user_id: int, config_id: int) -> dict:
    """把指定配置设为当前生效。"""
    _get_row(conn, user_id, config_id)
    conn.execute(
        "UPDATE user_llm_configs SET is_active = 0 WHERE user_id = ?", (user_id,)
    )
    conn.execute(
        "UPDATE user_llm_configs SET is_active = 1, updated_at = ? WHERE id = ? AND user_id = ?",
        (utc_now_iso(), config_id, user_id),
    )
    conn.commit()
    return _row_to_public(_get_row(conn, user_id, config_id))


def delete_config(conn: sqlite3.Connection, user_id: int, config_id: int) -> dict:
    """删除配置；若删除的是生效配置，自动把最新一份设为生效。"""
    row = _get_row(conn, user_id, config_id)
    was_active = bool(row["is_active"])
    conn.execute(
        "DELETE FROM user_llm_configs WHERE id = ? AND user_id = ?", (config_id, user_id)
    )
    if was_active:
        latest = conn.execute(
            "SELECT id FROM user_llm_configs WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if latest is not None:
            conn.execute(
                "UPDATE user_llm_configs SET is_active = 1 WHERE id = ?", (latest["id"],)
            )
    conn.commit()
    return {"deleted": config_id, "active_config_id": _active_id(conn, user_id)}


def _active_id(conn: sqlite3.Connection, user_id: int) -> int | None:
    """返回当前生效配置的 id。"""
    row = conn.execute(
        "SELECT id FROM user_llm_configs WHERE user_id = ? AND is_active = 1",
        (user_id,),
    ).fetchone()
    return int(row["id"]) if row else None


def build_provider(row: sqlite3.Row) -> llm_base.LLMProvider:
    """按配置构造 Provider 实例（解密密钥）。"""
    api_key = decrypt_secret(row["api_key_cipher"])
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=row["base_url"],
        model=row["model"],
        embedding_model=row["embedding_model"],
    )


def get_active_provider(conn: sqlite3.Connection, user_id: int) -> llm_base.LLMProvider | None:
    """返回用户当前生效的 Provider；没有配置时返回 None。"""
    row = conn.execute(
        "SELECT * FROM user_llm_configs WHERE user_id = ? AND is_active = 1",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return build_provider(row)


def test_config(
    conn: sqlite3.Connection,
    user_id: int,
    config_id: int | None = None,
    payload: dict | None = None,
) -> dict:
    """验证一份配置是否可用（可测未保存的草稿）。"""
    if payload is not None and payload.get("api_key"):
        data = _validate_payload(payload)
        provider = OpenAICompatibleProvider(
            api_key=data["api_key"],
            base_url=data["base_url"],
            model=data["model"],
            embedding_model=data["embedding_model"],
            timeout_seconds=30.0,
        )
        target_id = None
    else:
        if config_id is None:
            raise ApiError(400, "LLM_CONFIG_REQUIRED", "请先选择要测试的配置。")
        row = _get_row(conn, user_id, config_id)
        provider = build_provider(row)
        target_id = config_id

    try:
        result = provider.chat(
            [llm_base.ChatMessage(role="user", content="请只回复两个字：正常")],
            {"temperature": 0, "max_tokens": 16},
        )
    except llm_base.LLMError as exc:
        message = str(exc)
        if target_id is not None:
            conn.execute(
                "UPDATE user_llm_configs SET last_error = ?, updated_at = ? WHERE id = ?",
                (message[:500], utc_now_iso(), target_id),
            )
            conn.commit()
        return {"ok": False, "error": message, "model": provider.model}

    if target_id is not None:
        conn.execute(
            """UPDATE user_llm_configs
               SET last_verified_at = ?, last_error = NULL, updated_at = ?
               WHERE id = ?""",
            (utc_now_iso(), utc_now_iso(), target_id),
        )
        conn.commit()
    return {"ok": True, "reply": result.text[:100], "model": result.model}
