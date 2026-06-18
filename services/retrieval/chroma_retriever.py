import chromadb
from shared.contracts import Chunk, RetrievalResult, Retriever
from services.ingestion.embedder import BGEEmbedder


# Dense retrieval via Chroma
class ChromaRetriever(Retriever):
    def __init__(
        self, embedder: BGEEmbedder, chroma_path: str, collection: str = "documents"
    ):
        self.embedder = embedder
        client = chromadb.PersistentClient(path=chroma_path)
        self.col = client.get_or_create_collection(
            name=collection,
            metadata={"hnsm:space": "cosine"},
        )

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        results = self.col.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=min(top_k, self.col.count() or 1),
            include=["documents", "metadatas", "distances"],
        )
        chunks = [
            Chunk(
                id=results["ids"][0][i],
                text=results["documents"][0][i],
                metadata=results["metadatas"][0][i] or {},
                score=1.0 - results["distances"][0][i],
            )
            for i in range(len(results["ids"][0]))
        ]

        return RetrievalResult(
            chunks=chunks, query=query, retriever_used="chroma_dense"
        )

    def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self.col.upsert(
            ids=[c.id for c in chunks],
            embeddings=self.embedder.embed([c.text for c in chunks]),
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
