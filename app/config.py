from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/dataf1"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "change_me_in_production"
    FASTF1_CACHE_DIR: str = "/tmp/fastf1"
    API_BASE_URL: str = "http://localhost:8000"
    GROQ_API_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
