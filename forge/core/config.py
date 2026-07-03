"""
Forge Configuration Module

Centralized configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ForgeSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Cognee Cloud Configuration
    # -------------------------------------------------------------------------
    cognee_service_url: str = Field(
        default="https://api.cognee.ai",
        description="Cognee Cloud API endpoint",
    )
    cognee_api_key: str = Field(
        default="",
        description="Cognee Cloud API key",
    )

    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, gemini, etc.)",
    )
    llm_model: str = Field(
        default="openai/gpt-4o-mini",
        description="LLM model identifier",
    )
    llm_api_key: str = Field(
        default="",
        description="LLM provider API key",
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature",
    )

    # -------------------------------------------------------------------------
    # Embedding Configuration
    # -------------------------------------------------------------------------
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider",
    )
    embedding_model: str = Field(
        default="openai/text-embedding-3-large",
        description="Embedding model identifier",
    )
    embedding_dimensions: int = Field(
        default=3072,
        description="Embedding vector dimensions",
    )

    # -------------------------------------------------------------------------
    # Application Configuration
    # -------------------------------------------------------------------------
    forge_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    forge_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application log level",
    )
    forge_data_dir: Path = Field(
        default=Path("./data"),
        description="Directory for data files",
    )

    # -------------------------------------------------------------------------
    # Web UI Configuration
    # -------------------------------------------------------------------------
    forge_web_host: str = Field(
        default="0.0.0.0",
        description="Web UI host address",
    )
    forge_web_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Web UI port",
    )

    # -------------------------------------------------------------------------
    # Dataset Configuration
    # -------------------------------------------------------------------------
    incidents_data_path: Path = Field(
        default=Path("./data/incidents.json"),
        description="Path to incidents dataset",
    )
    architecture_data_path: Path = Field(
        default=Path("./data/architecture.json"),
        description="Path to architecture dataset",
    )
    postmortem_data_path: Path = Field(
        default=Path("./data/postmortems.json"),
        description="Path to postmortems dataset",
    )

    # -------------------------------------------------------------------------
    # Dataset Names (Cognee datasets)
    # -------------------------------------------------------------------------
    incidents_dataset: str = Field(
        default="forge_incidents",
        description="Cognee dataset name for incidents",
    )
    architecture_dataset: str = Field(
        default="forge_architecture",
        description="Cognee dataset name for architecture",
    )
    postmortems_dataset: str = Field(
        default="forge_postmortems",
        description="Cognee dataset name for postmortems",
    )


# Global settings instance
settings = ForgeSettings()


def get_settings() -> ForgeSettings:
    """Get the global settings instance."""
    return settings
