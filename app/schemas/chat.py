import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    patient_id: uuid.UUID | None = None
    message: str = Field(..., min_length=1, max_length=4000)


class RetrievedSource(BaseModel):
    document_id: str
    snippet: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[RetrievedSource]
    used_patient_history: bool
    disclaimer: str
    escalate_to_clinician: bool = False
