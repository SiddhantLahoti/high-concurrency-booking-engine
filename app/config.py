from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:superpassword@localhost:5432/flash_sale_db"
    REDIS_URL: str = "redis://localhost:6379/0"

settings = Settings()