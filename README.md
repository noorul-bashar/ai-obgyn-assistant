# AI OB-GYN Clinical Decision-Support Assistant

Backend implementing the workflow from the whiteboard sketch:

**Ingestion:** `PDF/Image -> clean -> chunk -> embed -> upsert into vector DB (Pinecone)`
**Runtime:** `front-end query + patient history (relational DB) -> RAG -> LLM chain -> guardrails -> output -> front end`

## Architecture

```
app/
├── main.py                     FastAPI app
├── config.py                   Settings (env-driven)
├── api/v1/endpoints/           chat, patients, documents, health
├── db/                         SQLAlchemy models + session (patient history)
├── schemas/                    Pydantic request/response models
├── repositories/                DB access layer (patients, history)
├── services/
│   ├── ingestion/              loaders -> cleaner -> chunker -> embedder -> pipeline
│   ├── rag/                    vector_store (Pinecone), retriever, prompt_builder, rag_pipeline
│   ├── llm/                    LLM client interface + Anthropic implementation + the "chain"
│   └── safety/                 guardrails (urgent-symptom escalation, low-confidence fallback)
└── orchestrator/                ties it all together for the /chat endpoint
scripts/                        ingest_documents.py, init_db.py, init_vector_store.py
migrations/                     Alembic (versioned schema changes)
tests/
```

## Design notes — how this maps to the sketch

- **Separate ingestion pipeline**: `services/ingestion/` has no FastAPI dependency, so it runs
  both from the `/documents/upload` endpoint and standalone via `scripts/ingest_documents.py` —
  useful once ingestion volume outgrows the web process.
- **Patient data lifecycle**: the `patients` endpoints include a hard `DELETE`
  (`repositories/patient_repository.py`) for deletion/right-to-be-forgotten requests, alongside
  create/read/update — matching the "delete and resend flexible personal data" note.
- **Failsafe/fallback**: implemented as `services/safety/guardrails.py` — keyword-based
  urgent-symptom detection plus a low-retrieval-confidence fallback message. This was crossed out
  in the sketch, so it's kept intentionally minimal (a few regex patterns, no external calls);
  delete the module and its two call sites in `clinical_chain.py` if you'd rather not have it.
- **LLM provider**: the sketch didn't name one, so `services/llm/base.py` defines an interface and
  `anthropic_client.py` implements it with Claude — swap in another provider by implementing the
  same interface, no other file changes needed.
- **Lazy client construction**: Pinecone/Voyage/Anthropic clients are built once on first real
  request (via cached FastAPI dependencies), not at import time — so `/health` and the test suite
  run without any live credentials.

## Setup

1. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`, `VOYAGE_API_KEY`,
   `DATABASE_URL`.
2. `docker compose up -d db` (or point `DATABASE_URL` at your own Postgres).
3. `pip install -r requirements.txt`
4. `python scripts/init_db.py` for a quick local start, or set up Alembic properly for anything
   beyond local dev: `alembic revision --autogenerate -m "init"` then `alembic upgrade head`.
5. `python scripts/init_vector_store.py` — one-time Pinecone index creation.
6. `uvicorn app.main:app --reload`
7. Ingest reference material: `python scripts/ingest_documents.py --folder ./data/guidelines`

Run tests with `pytest` — they're fully mocked against Pinecone/Anthropic/Postgres, so no live
credentials are needed to run the suite.

## Before this touches real patients

- Every endpoint expects an `X-API-Key` header (`app/core/security.py`) — replace with proper
  OAuth2/JWT tied to your clinic's identity provider before deployment.
- The chain is designed to produce **decision support for the clinician to review**, not an
  autonomous diagnosis — `guardrails.py` and the system prompt both reinforce that framing, but the
  UI/workflow around it should keep a clinician in the loop before anything reaches a patient.
- Confirm data handling (storage, access logging, retention, deletion) against whatever regulatory
  regime applies to your deployment (HIPAA, GDPR, or local equivalents) — this scaffold gives you
  the hooks (e.g. hard delete, audit-friendly status tracking on ingested documents) but not a
  compliance sign-off.
- `pdf/image -> clean -> chunk -> embed` currently OCRs images with local Tesseract — fine for a
  prototype, but review accuracy on real scanned clinical documents before relying on it.

## Package notes

`pinecone` (not the deprecated `pinecone-client`) is on its v9 SDK, which introduced
`pc.index(name)` for data operations and a separate `pc.indexes.*` namespace for index management
— both are already wired up correctly in this codebase. If `scripts/init_vector_store.py` errors
on your installed version, check https://sdk.pinecone.io/python/ for the current index-management
calls; the always-on request path (`app/services/rag/vector_store.py`) doesn't depend on that part
of the API.
