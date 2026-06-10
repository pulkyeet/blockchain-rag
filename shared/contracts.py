from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

# Enums

class ToolName(str, Enum):
    VECTOR_RETRIEVAL = "vector_retrieval"
    GRAPH_QUERY = "graph_query"
    TEXT_TO_SQL = "text_to_sql"
    CODE_SANDBOX = "code_sandbox"

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    SELF_HOSTED = "self_hosted"

# Core Data Models

class Chunk(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0

class RetrievalResult(BaseModel):
    chunks: list[Chunk]
    query: str
    retriever_used: str

class ToolResult(BaseModel):
    tool: ToolName
    output: Any
    error: str | None = None
    latency_ms: float = 0.0

class AgentState(BaseModel):
    query: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    final_answer: str | None = None
    total_tokens: int = 0
    iteration: int = 0

# Abstract Base Classes

class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        ...

class Tool(ABC):
    name: ToolName

    @abstractmethod
    def run(self, input: dict[str, Any]) -> ToolResult:
        ...