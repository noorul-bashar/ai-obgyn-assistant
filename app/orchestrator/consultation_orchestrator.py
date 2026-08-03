"""
Top-level coordinator matching the whiteboard flow:

  front-end query + patient history (relational DB)
        -> RAG system (Pinecone retrieval)
        -> LLM chain
        -> guardrails
        -> output back to the front end
"""
import uuid

from sqlalchemy.orm import Session

from app.repositories.history_repository import get_history_for_patient, summarize_history
from app.schemas.chat import ChatResponse, RetrievedSource
from app.services.llm.clinical_chain import ClinicalDecisionChain
from app.services.rag.rag_pipeline import RAGPipeline


class ConsultationOrchestrator:
    def __init__(
        self,
        rag_pipeline: RAGPipeline | None = None,
        clinical_chain: ClinicalDecisionChain | None = None,
    ):
        self.rag_pipeline = rag_pipeline or RAGPipeline()
        self.clinical_chain = clinical_chain or ClinicalDecisionChain()

    def handle_query(self, db: Session, patient_id: uuid.UUID | None, message: str) -> ChatResponse:
        history_entries = []
        if patient_id is not None:
            history_entries = get_history_for_patient(db, patient_id)

        if patient_id is not None and history_entries:
            history_summary = summarize_history(history_entries)
        elif patient_id is not None:
            history_summary = "No prior visits on record for this patient."
        else:
            history_summary = "General consultation — no patient selected or patient not in database."

        rag_result = self.rag_pipeline.build(user_query=message, patient_history_summary=history_summary)
        chain_result = self.clinical_chain.run(rag_result=rag_result, raw_query=message)

        return ChatResponse(
            answer=chain_result.answer,
            sources=[
                RetrievedSource(document_id=s["id"], snippet=s["text"][:300], relevance_score=s["score"])
                for s in chain_result.sources
            ],
            # Patient history is intentionally excluded from the strict
            # vector-database-only answer path.
            used_patient_history=False,
            disclaimer=chain_result.disclaimer,
            escalate_to_clinician=chain_result.escalate_to_clinician,
        )
