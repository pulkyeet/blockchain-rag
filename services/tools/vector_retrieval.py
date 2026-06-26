from shared.contracts import Tool, ToolName, ToolResult
from services.retrieval.chroma_retriever import ChromaRetriever
import time


class VectorRetrievalTool(Tool):
    name = ToolName.VECTOR_RETRIEVAL

    def __init__(self, retriever: ChromaRetriever):
        self.retriever = retriever

    def run(self, input: dict) -> ToolResult:
        start = time.time()

        try:
            result = self.retriever.retrieve(
                input["question"], top_k=input.get("top_k", 5)
            )
            output = [
                {"text": c.text, "score": c.score, "metadata": c.metadata}
                for c in result.chunks
            ]
            return ToolResult(
                tool=self.name, output=output, latency_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ToolResult(
                tool=self.name,
                output=None,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )
