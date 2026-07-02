from pathlib import Path
from pydantic_settings import BaseSettings

# Always resolve .env relative to this file's location (backend/app/core/ → backend/.env)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    perplexity_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = "researchmind-index"
    app_env: str = "development"
    default_budget_usd: float = 1.00
    groq_model: str = "llama-3.3-70b-versatile"
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.5-flash"
    perplexity_model: str = "sonar-pro"

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()
