import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.api.v1.endpoints.documents as documents_endpoint
from app.api.v1.endpoints.chat import get_orchestrator
from app.api.v1.endpoints.documents import get_ingestion_pipeline
from app.db.session import get_db
from app.main import app
from app.schemas.chat import ChatResponse

client = TestClient(app)


class _FakeOrchestrator:
    def handle_query(self, db, patient_id, message):
        return ChatResponse(
            answer="stub answer",
            sources=[],
            used_patient_history=False,
            disclaimer="stub disclaimer",
            escalate_to_clinician=False,
        )


@pytest.fixture(autouse=True)
def _override_external_dependencies():
    """
    Every test in this module runs against a fake orchestrator and no real
    DB session, so none of them can accidentally reach Pinecone, Voyage,
    Anthropic, or Postgres.
    """
    app.dependency_overrides[get_orchestrator] = lambda: _FakeOrchestrator()
    app.dependency_overrides[get_db] = lambda: None
    yield
    app.dependency_overrides.clear()


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_requires_api_key():
    response = client.post(
        "/api/v1/chat/",
        json={"patient_id": str(uuid.uuid4()), "message": "hi"},
    )
    assert response.status_code in (401, 422)


def test_chat_with_valid_key_returns_stubbed_answer():
    response = client.post(
        "/api/v1/chat/",
        json={"patient_id": str(uuid.uuid4()), "message": "hi"},
        headers={"X-API-Key": "change-me"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "stub answer"


def test_chat_without_patient_id():
    response = client.post(
        "/api/v1/chat/",
        json={"message": "hi general query"},
        headers={"X-API-Key": "change-me"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "stub answer"


def test_upload_pipeline_initialization_failure_is_reported_as_503(monkeypatch):
    def fail_to_initialize():
        raise RuntimeError("Voyage is unavailable")

    get_ingestion_pipeline.cache_clear()
    monkeypatch.setattr(documents_endpoint, "IngestionPipeline", fail_to_initialize)

    with pytest.raises(HTTPException) as exc_info:
        get_ingestion_pipeline()

    assert exc_info.value.status_code == 503
    assert "Voyage is unavailable" in exc_info.value.detail
    get_ingestion_pipeline.cache_clear()
