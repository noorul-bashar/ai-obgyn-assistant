from app.services.llm.clinical_chain import ClinicalDecisionChain, NO_INDEXED_CONTEXT_ANSWER
from app.services.rag.rag_pipeline import RAGResult


def test_chain_does_not_call_llm_without_vector_context():
    class LLM:
        def generate(self, **kwargs):
            raise AssertionError("LLM must not be called without Pinecone context")

    result = ClinicalDecisionChain(llm_client=LLM()).run(
        RAGResult(system_prompt="system", user_prompt="prompt", sources=[], has_confident_context=False),
        raw_query="What are male sex organs?",
    )

    assert result.answer == NO_INDEXED_CONTEXT_ANSWER
    assert result.sources == []


def test_chain_calls_llm_only_when_vector_context_exists():
    class LLM:
        def generate(self, **kwargs):
            return "Supported fact [Source 1]."

    source = {"id": "vector-1", "score": 0.9, "text": "Evidence", "metadata": {}}
    result = ClinicalDecisionChain(llm_client=LLM()).run(
        RAGResult(system_prompt="system", user_prompt="prompt", sources=[source], has_confident_context=True),
        raw_query="Question",
    )

    assert result.answer == "Supported fact [Source 1]."
