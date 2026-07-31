import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://rethread:rethread@localhost:5432/rethread")
    GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")
    SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me")
    JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "168"))
    GEOAPIFY_CACHE_TTL_SECONDS = int(os.environ.get("GEOAPIFY_CACHE_TTL_SECONDS", "3600"))
    PORT = int(os.environ.get("PORT", "8000"))


config = Config()
