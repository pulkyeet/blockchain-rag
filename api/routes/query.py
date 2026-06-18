import json
from openai import OpenAI
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from api.deps import get_retriever
from services.retrieval.chroma_retriever import ChromaRetriever
from config import settings

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

        client = OpenAI(api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url)
        stream = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {req.query}",
                },
            ],
            stream=True,
            max_tokens=1024,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")
