"""
bot/config.py — Environment variable loading and Settings model.
Reads all configuration from environment variables (or .env file).
Raises RuntimeError on startup if required values are missing.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for BOT loaded from environment variables."""

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai", description="LLM provider: 'openai' or 'ollama'")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    llm_model: str = Field(default="gpt-4o", description="Primary LLM model name")
    llm_repair_model: str = Field(default="gpt-3.5-turbo", description="Model used for SQL repair")
    llm_temperature: float = Field(default=0.0, description="LLM sampling temperature")
    llm_max_tokens: int = Field(default=2000, description="Max tokens per LLM call")
    llm_base_url: Optional[str] = Field(default=None, description="Custom base URL (Ollama)")

    # ── Data ──────────────────────────────────────────────────────────────
    data_dir: str = Field(default="./data", description="Directory for Excel files")
    workbook_path: str = Field(default="", description="Default Excel workbook path")
    duckdb_path: str = Field(default=":memory:", description="DuckDB path (':memory:' or file path)")
    max_result_rows: int = Field(default=500, description="Max rows returned per query")
    max_file_size_mb: int = Field(default=50, description="Max upload size in MB")

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:8501")

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/bot.log")

    # ── Query Safety ──────────────────────────────────────────────────────
    max_query_timeout_seconds: int = Field(default=30)
    repair_max_attempts: int = Field(default=1)
    sql_row_limit: int = Field(default=500)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Allow empty key (user may use Ollama or set later)."""
        return v

    def validate_on_startup(self) -> None:
        """Call during app startup to fail fast on missing required config."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER=openai. "
                "Set it in your .env file or environment."
            )
        # Ensure data directory exists
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        # Ensure log directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Global singleton — imported everywhere
settings = Settings()
