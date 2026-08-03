from dataclasses import dataclass

from app.services.rag.prompt_builder import CLINICAL_SYSTEM_PROMPT, build_clinical_prompt
from app.services.rag.retriever import ClinicalRetriever


@dataclass
class RAGResult:
    system_prompt: str
    user_prompt: str
    sources: list[dict]
    has_confident_context: bool


class RAGPipeline:
    def __init__(self, retriever: ClinicalRetriever | None = None):
        self.retriever = retriever or ClinicalRetriever()

    def build(self, user_query: str, patient_history_summary: str) -> RAGResult:
        matches = self.retriever.retrieve(user_query)
        prompt = build_clinical_prompt(user_query, matches, patient_history_summary)

        return RAGResult(
            system_prompt=CLINICAL_SYSTEM_PROMPT,
            user_prompt=prompt,
            sources=matches,
            has_confident_context=len(matches) > 0,
        )
