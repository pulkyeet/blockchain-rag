import hashlib
import json
import uuid
import psycopg
from psycopg.types.json import Jsonb

from services.ingestion.chunker import TokenChunker
from services.retrieval.chroma_retriever import ChromaRetriever


class IngestPipeline:
    def __init__(self, chunker: TokenChunker, retriever: ChromaRetriever, pg_url: str):
        self.chunker = chunker
        self.retriever = retriever
        self.pg_url = pg_url

    def ingest(self, text: str, source: str, doc_type: str) -> dict:
        checksum = hashlib.sha256(text.encode()).hexdigest()

        with psycopg.connect(self.pg_url) as conn:
            # idempotency: if some content is already ingested, SKIP
            row = conn.execute(
                "SELECT id FROM documents WHERE checksum = %s", (checksum,)
            ).fetchone()
            if row:
                return {
                    "document_id": str(row[0]),
                    "chunks_created": 0,
                    "status": "already exists",
                }

            doc_id: uuid.UUID = conn.execute(
                "INSERT INTO documents (source, doc_type, checksum) VALUES (%s, %s, %s) RETURNING id",
                (source, doc_type, checksum),
            ).fetchone()[0]

            chunks = self.chunker.chunk(
                text, metadata={"document_id": str(doc_id), "source": source}
            )

            for i, chunk in enumerate(chunks):
                conn.execute(
                    """INSERT INTO chunks (id, document_id, text, chunk_index, token_count, metadata)
                       VALUES (%s::uuid, %s, %s, %s, %s, %s)""",
                    (
                        chunk.id,
                        str(doc_id),
                        chunk.text,
                        i,
                        chunk.metadata.get("token_count", 0),
                        Jsonb(chunk.metadata),
                    ),
                )
            conn.commit()

        self.retriever.upsert(chunks)

        return {
            "document_id": str(doc_id),
            "chunks_created": len(chunks),
            "total_tokens": sum(c.metadata.get("token_count", 0) for c in chunks),
            "status": "ok",
        }
