"""
GraphRetriever implements a Retriever so graph traveral results can be fed back to RAG synthesis in the form of chunks alongside vector retrieval results from chromaDB.
It wraps up the GraphQueryTool's result into chunk/RetrievalResult, which in turn returns raw rows for direction consumption (direct or agent)
"""

import json

from neo4j import GraphDatabase

from config import settings
from shared.contracts import Chunk, Retriever, RetrievalResult
from services.tools.graph_query import GraphQueryTool


class GraphRetriever(Retriever):
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.tool = GraphQueryTool()

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        result = self.tool.run({"question": query})

        if result.error or not result.output:
            return RetrievalResult(chunks=[], query=query, retriever_used="graph")

        rows = result.output["rows"][:top_k]
        chunks = [
            Chunk(
                id=f"graph-{i}",
                text=json.dumps(row, default=str),
                metadata={"cypher": result.output["cypher"], "row_index": i},
                score=1.0,
            )
            for i, row in enumerate(rows)
        ]
        return RetrievalResult(chunks=chunks, query=query, retriever_used="graph")
