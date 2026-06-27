import json
from openai import OpenAI
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from api.deps import get_retriever
from services.retrieval.chroma_retriever import ChromaRetriever
from config import settings
from google import genai

router = APIRouter()

SYSTEM_PROMPT = (
    "You are an expert in blockchain, smart contracts, and DeFi protocols."
    "Answer using onle the provided context chunks. cite [Chunk N] inline."
    "If context is insufficient, say so explicitly."
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/query")
def query(req: QueryRequest, retriever: ChromaRetriever = Depends(get_retriever)):
    result = retriever.retrieve(req.query, req.top_k)
    context = "\n\n".join(
        f"[Chunk {i+1} | score = {c.score: .3f} | source = {c.metadata.get('source', '?')}]\n{c.text}"
        for i, c in enumerate(result.chunks)
    )

    def generate():
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': [c.model_dump() for c in result.chunks]})}\n\n"

        client = genai.Client(api_key=settings.google_api_key)
        stream = client.models.generate_content_stream(
            model="gemini-3.1-flash-lite",
            contents=f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {req.query}",
        )
        for chunk in stream:
            if chunk.text:
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"

        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")
