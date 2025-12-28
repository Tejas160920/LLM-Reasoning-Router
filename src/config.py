"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "LLM Reasoning Router"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/llm_router",
        description="PostgreSQL connection string (async)",
    )

    @field_validator("database_url")
    @classmethod
    def ensure_async_driver(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver and compatible SSL params."""
        # Convert postgresql:// to postgresql+asyncpg://
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Convert postgres:// to postgresql+asyncpg://
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)

        # asyncpg uses 'ssl' instead of 'sslmode'
        # Remove sslmode and channel_binding params (not supported by asyncpg)
        if "?" in v:
            base, params = v.split("?", 1)
            param_list = params.split("&")
            # Filter out incompatible params
            filtered_params = [
                p for p in param_list
                if not p.startswith("sslmode=") and not p.startswith("channel_binding=")
            ]
            # Add ssl=require for asyncpg
            filtered_params.append("ssl=require")
            v = base + "?" + "&".join(filtered_params)
        else:
            # No params, add ssl=require
            v = v + "?ssl=require"

        return v
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Gemini API
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key",
    )

    # Model Configuration
    fast_model: str = Field(
        default="gemini-2.0-flash",
        description="Fast/cheap model for simple prompts",
    )
    complex_model: str = Field(
        default="gemini-2.0-flash-thinking-exp",
        description="Complex/reasoning model for difficult prompts",
    )

    # Routing Thresholds
    complexity_threshold_low: int = Field(
        default=30,
        ge=0,
        le=100,
        description="Below this score: use fast model, no quality check",
    )
    complexity_threshold_high: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Above this score: use complex model directly",
    )

    # Quality Checking
    quality_threshold: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Below this quality score: escalate to complex model",
    )
    max_escalation_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum number of escalation attempts",
    )

    # Timeouts
    llm_timeout: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
        description="LLM request timeout in seconds",
    )

    # Cost Tracking (per 1M tokens, in USD)
    cost_flash_input: float = Field(default=0.075, ge=0)
    cost_flash_output: float = Field(default=0.30, ge=0)
    cost_pro_input: float = Field(default=1.25, ge=0)
    cost_pro_output: float = Field(default=5.00, ge=0)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings singleton.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
