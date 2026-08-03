from functools import lru_cache

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.session import get_db
from app.orchestrator.consultation_orchestrator import ConsultationOrchestrator
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(dependencies=[Depends(verify_api_key)])


@lru_cache
def get_orchestrator() -> ConsultationOrchestrator:
    """
    Resolved lazily through Depends() and cached: Pinecone/Voyage/Anthropic
    clients get built once, on the first real request — not at import time —
    so running unrelated endpoints (like /health) or importing this module
    in a test never requires those credentials to be present.
    """
    return ConsultationOrchestrator()


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator: ConsultationOrchestrator = Depends(get_orchestrator),
):
    """
    Front-end entry point: takes a clinician's question + patient_id, pulls
    history, runs RAG + the LLM chain, returns a guarded answer.
    """
    return orchestrator.handle_query(db, payload.patient_id, payload.message)
