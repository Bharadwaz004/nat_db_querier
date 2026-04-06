"""Application configuration loaded from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME = "NL-to-SQL AI Engine"
    VERSION = "1.0.0"

    # Paths
    DATA_DIR = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
    EMBEDDINGS_DIR = os.getenv("EMBEDDINGS_DIR", str(BASE_DIR / "embeddings"))
    GRAPH_DIR = os.getenv("GRAPH_DIR", str(BASE_DIR / "graph"))
    DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "sample_ecommerce.db"))
    SAMPLE_DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "sample_ecommerce.db"))  # never mutated

    # LLM Provider: "anthropic" or "huggingface"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    HF_API_KEY = os.getenv("HF_API_KEY", "")
    HF_API_URL = os.getenv("HF_API_URL", "https://router.huggingface.co/v1")
    HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

    # Retrieval
    TOP_K_TABLES = int(os.getenv("TOP_K_TABLES", "5"))
    TOP_K_COLUMNS = int(os.getenv("TOP_K_COLUMNS", "15"))

    # SQL Validation
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    # JWT (shared with Node.js gateway)
    JWT_SECRET = os.getenv("JWT_SECRET", "nlsql-super-secret-key-change-in-production")

    # Server
    HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
    PORT = int(os.getenv("FASTAPI_PORT", "8000"))

settings = Settings()
