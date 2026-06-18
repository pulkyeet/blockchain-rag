from fastapi import FastAPI
from api.routes import ingest, query

app = FastAPI(title="Blockchain RAG", version="0.1.0")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}