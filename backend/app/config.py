"""应用配置。

全部配置项来自环境变量（样例见仓库根目录 ``.env.example``），便于容器化部署；
测试通过环境变量覆盖并清空 ``get_settings`` 的缓存来切换到临时数据库。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 开发环境兜底密钥；生产环境必须通过环境变量替换
DEFAULT_JWT_SECRET = "dev-insecure-secret-change-me-0123456789"
# 文档示例里给出的占位密钥，同样不可用于生产
DOC_PLACEHOLDER_JWT_SECRET = "placeholder"
# 生产环境禁止使用的密钥集合（兜底值、文档占位值、空值）
INSECURE_JWT_SECRETS = frozenset({DEFAULT_JWT_SECRET, DOC_PLACEHOLDER_JWT_SECRET})


class Settings(BaseSettings):
    """运行期配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用信息
    app_name: str = "校园综合 AI 平台"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"

    # 数据目录：SQLite、上传文件、向量索引均与业务代码物理隔离
    data_dir: Path = Path("./data")
    db_path: Path | None = None

    # 认证
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # LLM Provider：首轮 deepseek，统一抽象接口，后续可扩展通义/智谱
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_embedding_model: str = "deepseek-embedding"

    # 每日配额（初期 30–50 次/日）
    daily_qa_limit: int = 30
    daily_chat_limit: int = 50

    # 允许跨域的前端来源，逗号分隔；同源部署（nginx 反代）时留空
    cors_origins: str = ""

    @model_validator(mode="after")
    def fill_default_secret_outside_production(self) -> Settings:
        """非生产环境下，密钥为空时回退到开发兜底密钥（生产环境由 validate_runtime 拦截）。"""
        if not self.jwt_secret.strip() and not self.is_production:
            self.jwt_secret = DEFAULT_JWT_SECRET
        return self

    @property
    def resolved_db_path(self) -> Path:
        """实际使用的 SQLite 文件路径。"""
        if self.db_path:
            return self.db_path
        return self.data_dir / "app.db"

    @property
    def files_dir(self) -> Path:
        """用户上传文件目录。"""
        return self.data_dir / "files"

    @property
    def index_dir(self) -> Path:
        """本地向量索引目录。"""
        return self.data_dir / "index"

    @property
    def cors_origin_list(self) -> list[str]:
        """解析后的跨域来源列表。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def uses_default_jwt_secret(self) -> bool:
        """是否仍在使用开发兜底密钥。"""
        return self.jwt_secret == DEFAULT_JWT_SECRET

    @property
    def is_insecure_jwt_secret(self) -> bool:
        """密钥是否为空或属于已知兜底/占位值。"""
        secret = self.jwt_secret.strip()
        return secret == "" or secret in INSECURE_JWT_SECRETS

    @property
    def is_production(self) -> bool:
        """是否以生产模式运行。"""
        return self.app_env.strip().lower() == "production"

    def ensure_dirs(self) -> None:
        """创建运行期目录（首次启动时调用）。"""
        for path in (self.data_dir, self.files_dir, self.index_dir):
            path.mkdir(parents=True, exist_ok=True)
        self.resolved_db_path.parent.mkdir(parents=True, exist_ok=True)

    def validate_runtime(self) -> None:
        """启动前校验：生产环境禁止使用兜底或占位 JWT 密钥。

        Raises:
            RuntimeError: 生产环境仍在使用不安全密钥时直接拒绝启动。
        """
        if not self.is_production:
            return
        if self.is_insecure_jwt_secret:
            raise RuntimeError(
                "生产环境禁止使用兜底或占位 JWT 密钥：请通过环境变量 JWT_SECRET 设置"
                "至少 32 字节的随机密钥（可用 openssl rand -hex 32 生成）。"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程内缓存的配置实例。"""
    return Settings()
