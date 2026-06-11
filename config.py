from pedantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_url: str = "postgresql://rag:rag@localhost:5432/blockchain_rag"
    chroma_path: str = "./data/chroma"
    anthropic_api_key: str = ""
    embedding_model: str = "BAAI/bge-base-en-v1.5"
    chunk_size: int = 512

    model_config = {"env_file": ".env"}

settings = Settings()