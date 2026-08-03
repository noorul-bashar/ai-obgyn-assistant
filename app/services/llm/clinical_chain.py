"""
The "chain" step from the design: takes the RAG-built prompt, calls the
LLM, and hands the raw draft to the safety layer before anything reaches
the front end.
"""
from dataclasses import dataclass

from app.services.llm.groq_client import get_llm_client
from app.services.llm.base import BaseLLMClient
from app.services.rag.rag_pipeline import RAGResult
from app.services.safety.guardrails import GuardrailResult, apply_guardrails

NO_INDEXED_CONTEXT_ANSWER = (
    "The indexed reference material does not contain enough information to answer this question."
)

@dataclass
class ClinicalChainResult:
    answer: str
    sources: list[dict]
    escalate_to_clinician: bool
    disclaimer: str


class ClinicalDecisionChain:
    def __init__(self, llm_client: BaseLLMClient | None = None):
        self.llm_client = llm_client or get_llm_client()

    def run(self, rag_result: RAGResult, raw_query: str) -> ClinicalChainResult:
        # With no matching vector context, do not call the LLM at all. This
        # prevents a model from answering from training knowledge instead of
        # the user's indexed material.
        if rag_result.has_confident_context:
            draft_answer = self.llm_client.generate(
                system_prompt=rag_result.system_prompt,
                user_prompt=rag_result.user_prompt,
            )
        else:
            draft_answer = NO_INDEXED_CONTEXT_ANSWER

        guarded: GuardrailResult = apply_guardrails(
            draft_answer=draft_answer,
            raw_query=raw_query,
            has_confident_context=rag_result.has_confident_context,
        )

        return ClinicalChainResult(
            answer=guarded.final_answer,
            sources=rag_result.sources,
            escalate_to_clinician=guarded.escalate,
            disclaimer=guarded.disclaimer,
        )
