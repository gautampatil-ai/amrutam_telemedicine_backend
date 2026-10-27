from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Amrutam Telemedicine API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://amrutam:amrutam@db:5432/amrutam"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARS"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
