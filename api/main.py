from fastapi import FastAPI
from api.routes import ingest, query
from api.routes.agent import router as agent_router

app = FastAPI(title="Blockchain RAG", version="0.1.0")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(agent_router)


@app.get("/health")
def health():
    return {"status": "ok"}