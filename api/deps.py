from functools import lru_cache
from openai import OpenAI

from config import settings
from shared.contracts import ToolName
from services.ingestion.chunker import TokenChunker
from services.ingestion.embedder import BGEEmbedder
from services.ingestion.pipeline import IngestPipeline
from services.retrieval.chroma_retriever import ChromaRetriever
from services.tools.vector_retrieval import VectorRetrievalTool
from services.tools.text_to_sql import TextToSQLTool
from services.tools.graph_query import GraphQueryTool
from services.agent.react_agent import ReActAgent


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


@lru_cache
def get_vector_tool() -> VectorRetrievalTool:
    return VectorRetrievalTool(get_retriever())


@lru_cache
def get_text_to_sql_tool() -> TextToSQLTool:
    return TextToSQLTool()


@lru_cache
def get_graph_query_tool() -> GraphQueryTool:
    return GraphQueryTool()


@lru_cache
def get_agent_llm_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
    )


@lru_cache
def get_agent() -> ReActAgent:
    tools = {
        ToolName.VECTOR_RETRIEVAL: get_vector_tool(),
        ToolName.TEXT_TO_SQL: get_text_to_sql_tool(),
        ToolName.GRAPH_QUERY: get_graph_query_tool(),
    }
    return ReActAgent(
        tools, get_agent_llm_client(), model="nvidia/nemotron-3-super-120b-a12b:free"
    )
