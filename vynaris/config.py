from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: str = Field(default="")

    database_url: str = Field(
        default="postgresql+asyncpg://vynaris:vynaris_dev_password_change_me@localhost:5432/vynaris",
    )
    database_url_sync: str = Field(default="")

    vynaris_host: str = Field(default="127.0.0.1")
    vynaris_port: int = Field(default=7878)
    vynaris_secret_key: str = Field(default="change-me-to-a-long-random-string-at-least-32-chars")
    vynaris_data_dir: Path = Field(default=Path("./vynaris-data"))
    vynaris_env: str = Field(default="dev")

    vynaris_model: str = Field(default="claude-sonnet-4-5")
    vynaris_planning_model: str = Field(default="claude-opus-4-5")

    # External channel adapters. Unset = adapter runs as a stub and UI shows "coming soon".
    discord_bot_token: str = Field(default="")
    discord_bot_invite_url: str = Field(default="")
    whatsapp_api_token: str = Field(default="")
    msteams_bot_token: str = Field(default="")
    gchat_service_account: str = Field(default="")
    slack_bot_token: str = Field(default="")

    # Integration credentials (per-connector). Unset = UI shows "Connect" but hints at missing config.
    gmail_client_id: str = Field(default="")
    gmail_client_secret: str = Field(default="")
    gmail_redirect_uri: str = Field(default="")
    google_sheets_client_id: str = Field(default="")
    x_api_key: str = Field(default="")

    # Fernet key for encrypting Integration.config_encrypted. Derived from vynaris_secret_key if blank.
    integration_encryption_key: str = Field(default="")

    @property
    def sync_database_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("+asyncpg", "+psycopg2").replace(
            "postgresql+psycopg2", "postgresql+psycopg2"
        ).replace("postgresql://", "postgresql+psycopg2://", 1) if "+asyncpg" in self.database_url else self.database_url

    @property
    def workspaces_dir(self) -> Path:
        return self.vynaris_data_dir / "workspaces"

    @property
    def logs_dir(self) -> Path:
        return self.vynaris_data_dir / "logs"

    @property
    def skills_dir(self) -> Path:
        # Anthropic-native location: `.claude/skills/<name>/SKILL.md`.
        # The Claude Agent SDK auto-discovers these when setting_sources=['project'].
        return Path(".claude/skills")

    def ensure_dirs(self) -> None:
        self.vynaris_data_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
