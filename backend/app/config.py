"""Configuration settings for Scooper CMS"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Database
    DATABASE_URL: str = "sqlite:///./scooper.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CMS Authentication
    CMS_USERNAME: str = "admin"
    CMS_PASSWORD: str = "changeme"
    
    # CORS
    CORS_ORIGINS: List[str] = []
    
    # Debug mode
    DEBUG: bool = True
    
    # Static files
    STATIC_DIR: str = "static"
    UPLOADS_DIR: str = "static/uploads"


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
