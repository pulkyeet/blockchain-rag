from functools import lru_cache
from config import settings
from services.ingestion.chunker import TokenChunker
from services.ingestion.embedder import BGEEmbedder
from services.ingestion.pipeline import IngestPipeline
from services.retrieval.chroma_retriever import ChromaRetriever


@lru_cache
def get_embedder() -> BGEEmbedder:
    return BGEEmbedder(settings.embedding_model)  


@lru_cache
def get_retriever() -> ChromaRetriever:
    return ChromaRetriever(get_embedder(), settings.chroma_path)


@lru_cache
def get_pipeline() -> IngestPipeline:
    return IngestPipeline(
        TokenChunker(settings.chunk_size, settings.chunk_overlap),
        get_retriever(),
        settings.postgres_url,
    )