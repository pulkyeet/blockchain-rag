from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.deps import get_pipeline
from services.ingestion.pipeline import IngestPipeline

router = APIRouter()

class IngestRequest(BaseModel):
    text: str
    source: str = "manual"
    doc_type: str = "docs"

@router.post("/ingest")
def ingest(req: IngestRequest, pipeline: IngestPipeline = Depends(get_pipeline)):
    if not req.text.strip():
        raise HTTPException(400, "text cannot be empty")
    return pipeline.ingest(req.text, req.source, req.doc_type)