from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: str = "postgresql://rag:yeet2178@localhost:5432/bc_rag"
    chroma_path: str = "./data/chroma"
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    chunk_size: int = 512
    chunk_overlap: int = 50

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
