# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_URL: str = os.getenv("DB_URL", "sqlite:///./credit_app.db")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    API_V1_STR: str = "/v1"
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
