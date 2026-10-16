from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str = "sqlite:///./claimiq.db"
    upload_dir: str = "uploads"

    vector_db_dir: str = "vector_db"
    embedding_model: str = "all-MiniLM-L6-v2"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 5

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()