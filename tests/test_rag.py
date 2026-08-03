from app.services.rag.prompt_builder import build_clinical_prompt
from app.services.rag.retriever import ClinicalRetriever


def test_prompt_includes_history_and_context():
    prompt = build_clinical_prompt(
        user_query="Is follow-up needed?",
        retrieved_context=[{"text": "ACOG guideline excerpt", "score": 0.81}],
        patient_history_summary="- 2026-06-10: spotting, subchorionic hematoma",
    )
    assert "Is follow-up needed?" in prompt
    assert "ACOG guideline excerpt" in prompt
    assert "subchorionic hematoma" not in prompt
    assert "Patient history" not in prompt


def test_prompt_flags_missing_context():
    prompt = build_clinical_prompt(
        user_query="Any question",
        retrieved_context=[],
        patient_history_summary="No prior visits on record.",
    )
    assert "No sufficiently relevant reference material" in prompt


def test_retriever_expands_best_child_matches_to_distinct_parent_context(monkeypatch):
    class Embeddings:
        def embed_query(self, text):
            return [0.1]

    class VectorStore:
        def query(self, vector, top_k, metadata_filter):
            assert top_k == 8  # requested two parents × candidate multiplier four
            assert metadata_filter == {
                "embedding_provider": "clip",
                "embedding_model": "openai/clip-vit-base-patch32",
            }
            return [
                {
                    "id": "child-1",
                    "score": 0.91,
                    "text": "small matching child",
                    "metadata": {"parent_id": "parent-1", "parent_text": "complete parent one"},
                },
                {
                    "id": "child-2",
                    "score": 0.90,
                    "text": "another child from the same parent",
                    "metadata": {"parent_id": "parent-1", "parent_text": "complete parent one"},
                },
                {
                    "id": "child-3",
                    "score": 0.82,
                    "text": "small matching child",
                    "metadata": {"parent_id": "parent-2", "parent_text": "complete parent two"},
                },
            ]

    monkeypatch.setattr("app.services.rag.retriever.settings.MIN_RELEVANCE_SCORE", 0.7)
    monkeypatch.setattr("app.services.rag.retriever.settings.CHILD_RETRIEVAL_MULTIPLIER", 4)
    retriever = ClinicalRetriever(embedding_client=Embeddings(), vector_store=VectorStore())

    matches = retriever.retrieve("What are male reproductive organs?", top_k=2)

    assert [match["text"] for match in matches] == ["complete parent one", "complete parent two"]
