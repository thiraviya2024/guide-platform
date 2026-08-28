# app/core/config.py
"""
Configuration management for LIFE SAVER platform.
Uses Pydantic Settings with environment variable support.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os
from pathlib import Path

# ✅ Load .env before settings
try:
    from dotenv import load_dotenv
    # Resolve relative to this source file so uvicorn, tests, and Render do not
    # depend on the process working directory to find the project .env file.
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    # python-dotenv not installed - skip
    pass


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via .env file or environment variables.
    """
    
    # ============================================================
    # APPLICATION
    # ============================================================
    APP_NAME: str = "LIFE SAVER"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered Hospital Clinical Decision Support System"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # ============================================================
    # API
    # ============================================================
    API_V1_PREFIX: str = "/api/v1"
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"
    
    # ============================================================
    # DATABASE
    # ============================================================
    DATABASE_URL: str = Field(
        default="postgresql://localhost:5432/lifesaver",
        description="PostgreSQL connection string"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False
    
    # ============================================================
    # SECURITY & JWT
    # ============================================================
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT signing key - MUST change in production",
        min_length=32
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    
    ADMIN_RULES_TOKEN: Optional[str] = None

    # ============================================================
    # CORS - FIXED
    # ============================================================
    ALLOWED_ORIGINS: List[str] = [
        "*"  # Allow all origins for development
    ]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    ALLOW_CREDENTIALS: bool = False  # Must be False with "*"
    
    # ============================================================
    # LLM / AI
    # ============================================================
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # ✅ Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"
    
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    DEFAULT_LLM_PROVIDER: str = "groq"  # groq, gemini, openai, ollama, deepseek

    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = "mistral-small-latest"
    
    # ✅ Multi-AI Configuration
    USE_MULTI_AI: bool = True  # Enable multi-AI orchestration
    # Mistral is available as an explicit opt-in provider, but an invalid or
    # unused Mistral credential must not make it part of the normal failover.
    AI_PROVIDER_ORDER: str = "groq,gemini"
    
    # ============================================================
    # FILE UPLOAD
    # ============================================================
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".doc", ".txt", 
        ".xlsx", ".xls", ".csv",
        ".png", ".jpg", ".jpeg", ".gif", ".tiff"
    ]
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/tiff",
    ]
    
    # ============================================================
    # OCR
    # ============================================================
    OCR_ENGINE: str = "easyocr"  # easyocr, tesseract, paddleocr
    OCR_LANGUAGE: List[str] = ["en"]
    OCR_GPU: bool = False
    TESSERACT_CMD: str = "tesseract"
    
    # ============================================================
    # MIMIC-IV
    # ============================================================
    MIMIC_DATABASE_URL: Optional[str] = None
    MIMIC_USE_DEMO: bool = True
    MIMIC_DEMO_SIZE: int = 100  # number of patients to use from demo
    
    # ============================================================
    # REDIS (for caching, rate limiting, session)
    # ============================================================
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds
    
    # ============================================================
    # EMAIL
    # ============================================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@lifesaver.ai"
    
    # ============================================================
    # LOGGING
    # ============================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/lifesaver.log"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # ============================================================
    # VALIDATORS
    # ============================================================
    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, v: object) -> object:
        """Accept deployment labels without making settings construction fail."""
        if isinstance(v, str) and v.strip().lower() in {"release", "production"}:
            return False
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is not the default in production."""
        if v == "your-secret-key-change-in-production" and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("SECRET_KEY must be changed in production!")
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is properly formatted."""
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must use postgresql:// scheme")
        return v

    @field_validator("ADMIN_RULES_TOKEN")
    @classmethod
    def validate_admin_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate admin token format if provided."""
        if v is not None and len(v) < 16:
            raise ValueError("ADMIN_RULES_TOKEN must be at least 16 characters long")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Singleton instance
settings = Settings()


# ============================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# ============================================================
from functools import lru_cache


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton
    """
    return settings
