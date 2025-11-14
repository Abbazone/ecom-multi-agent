# config/settings.py

from typing import Literal, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OrderAPIConfig(BaseModel):
    """Config for the external Order API (Beeceptor / real service)."""

    base_url: str = Field(..., description="Base URL of the order API")
    timeout_seconds: float = 5.0
    max_retries: int = 3
    backoff_factor: float = 0.5  # e.g. for tenacity: 0.5, 1, 2...


class OpenAIConfig(BaseModel):
    """Config for OpenAI chat + embeddings."""

    api_key: str = Field(..., repr=False)
    chat_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    request_timeout_seconds: float = 15.0
    max_retries: int = 3
    temperature: float = 0.1
    backoff_factor: float = 0.5
    resolver_min_conf: float = 0.6


class VectorDBConfig(BaseModel):
    """Config for Chroma (or other vector DB)."""

    implementation: Literal["chroma"] = "chroma"
    persist_directory: str = "./data/chroma"
    collection_name: str = "kb_faq"
    embedding_dim: int = 1536  # 1536 for text-embedding-3-*
    enable_embeddings: bool = True
    use_openai_embeddings: bool = True
    kb_top_k: int = 3
    kb_min_score: float = 0.35


class OrchestratorConfig(BaseModel):
    """Config for the multi-agent orchestrator."""

    max_history_turns: int = 8
    enable_tools: bool = True
    trace_logging: bool = False  # enable for deep debugging


class LoggingConfig(BaseModel):
    """Basic logging config."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logging: bool = False


class ModulesConfig(BaseModel):
    router_name: str
    kb_name: str
    order_api_name: str


class Settings(BaseSettings):
    """Top-level app settings loaded from environment / .env."""

    # High-level runtime env
    env: Literal["dev", "staging", "prod"] = "dev"

    # Nested configs
    modules: ModulesConfig
    order_api: OrderAPIConfig
    openai: OpenAIConfig
    vectordb: VectorDBConfig = VectorDBConfig()
    orchestrator: OrchestratorConfig = OrchestratorConfig()
    logging: LoggingConfig = LoggingConfig()

    # pydantic-settings v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",              # all vars start with APP_
        env_nested_delimiter="__",      # APP_ORDER_API__BASE_URL, etc.
        case_sensitive=False,
    )


# Single global instance you import everywhere
settings = Settings()

print(settings)
