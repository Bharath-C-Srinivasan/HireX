"""Application Configuration."""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HIREX AI Interview Workflow & Evaluation API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./hirex.db"
    DB_ECHO: bool = False
    
    # Security & JWT
    SECRET_KEY: str = "hirex-super-secret-development-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # LLM Adapter
    LLM_ADAPTER_TYPE: str = "deterministic"  # 'deterministic', 'openai', etc.
    LLM_ADAPTER_VERSION: str = "hirex-adapter-v1.2.0"
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_MAX_RETRIES: int = 2
    OPENAI_API_KEY: Optional[str] = None
    
    # Rubric Score Bounds
    SCORE_MIN: int = 1
    SCORE_MAX: int = 5
    
    # LiveKit Mock/Real Credentials
    LIVEKIT_API_KEY: str = "livekit_hirex_key"
    LIVEKIT_API_SECRET: str = "livekit_hirex_secret_32_character_key_min"
    LIVEKIT_WEBHOOK_SECRET: str = "whsec_hirex_webhook_secret_key"
    
    # Idempotency Lock Expiration (seconds)
    IDEMPOTENCY_LOCK_SECONDS: int = 60
    
    # Background Worker simulation
    EVALUATION_ASYNC_MODE: bool = False  # If true, runs via background worker or BackgroundTasks
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
