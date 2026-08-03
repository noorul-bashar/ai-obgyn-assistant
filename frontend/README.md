# AI OB-GYN Clinical Assistant — Streamlit Front End

A clinician-facing UI for the FastAPI backend in `../app`. It's a plain HTTP client —
`api_client.py` calls the backend's REST API exactly as documented in `../README.md`;
no backend code is imported.

```
frontend/
├── streamlit_app.py     Home: connection status, quick stats, navigation
├── api_client.py         All HTTP calls to the backend (OBGYNClient, APIError)
├── utils.py               Session-state, sidebar, and shared UI helpers
├── pages/
│   ├── 1_💬_Consultation.py     POST /chat/
│   ├── 2_🧑‍⚕️_Patients.py         /patients CRUD
│   ├── 3_📖_Medical_History.py  /patients/{id}/history
│   └── 4_📄_Documents.py         POST /documents/upload
├── .streamlit/config.toml
├── requirements.txt
└── Dockerfile
```

## Run it

**Locally, against a backend already running on `localhost:8000`:**

```bash
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`). In the sidebar, set the
**Backend URL** (default `http://localhost:8000`) and **API key** (must match `API_KEY` in
the backend's `.env` — `change-me` by default) and click **Test connection**.

**Both services together, with Docker Compose (from the project root):**

```bash
docker compose up -d
```

This now also builds and starts `frontend` on port 8501, pointed at the `api` service over
the compose network and sharing the same `API_KEY` from the root `.env`. `db` and `api`
behave exactly as before — nothing about the existing backend setup changed.

You can also override the defaults via environment variables before running Streamlit
directly (`OBGYN_API_BASE_URL`, `OBGYN_API_KEY`) — this is what the Docker Compose service
uses instead of the sidebar.

## How it maps to the backend

| Page | Backend endpoint(s) |
|---|---|
| Consultation | `POST /api/v1/chat/` |
| Patients | `GET/POST /api/v1/patients/`, `GET/PATCH/DELETE /api/v1/patients/{id}` |
| Medical History | `GET/POST /api/v1/patients/{id}/history` |
| Documents | `POST /api/v1/documents/upload` |

Every request except `/health` sends an `X-API-Key` header, matching `app/core/security.py`.
`api_client.py` translates backend error responses (401 / 404 / 422 / 503, plus connection
failures and timeouts) into a single `APIError` with a message that's safe to show directly
in the UI.

The **active patient** (name + id) is kept in `st.session_state` and shared across pages, so
selecting a patient in one tab carries over to the others. Per-patient chat transcripts are
also kept in session state, keyed by patient id.

## Things worth knowing about the backend contract

Found while wiring this up — not bugs exactly, just sharp edges to be aware of:

- **`patient_id` is required for chat.** `ChatRequest.patient_id` isn't optional, so there's
  no "general" chat mode — a patient must exist before the Consultation page can be used.
  The UI enforces this and points to the Patients page if none is selected.
- **Chat isn't persisted.** `POST /chat/` doesn't write anything to the database — closing
  the tab loses the transcript. The Consultation page says this explicitly and links to
  Medical History if a clinician wants part of the conversation kept on the record.
- **`clinician_notes` is write-only.** `MedicalHistoryCreate` accepts it, but
  `MedicalHistoryOut` doesn't return it, so it can never be displayed after saving. The Add
  Visit form still collects it (it's presumably used or reported on elsewhere) but says so.
- **No document list endpoint.** `POST /documents/upload` is the only `/documents` route, so
  the Documents page can only show what's been uploaded in the current browser session, not
  a full ingestion history.
- **`/documents/upload` runs synchronously** (load → clean → chunk → embed → upsert on the
  request thread, per the docstring in `app/api/v1/endpoints/documents.py`), so large PDFs
  can take a while — the upload button shows a spinner rather than a progress bar.

## Notes

- CORS is a non-issue here: this Python process calls the backend directly with `requests`,
  not from JavaScript in the browser, so the backend's `allow_origins=["*"]` in `app/main.py`
  isn't even exercised by this app.
- `frontend/api_client.py` hardcodes `/api/v1` to match `Settings.API_V1_PREFIX` in
  `app/config.py`. If that prefix ever changes on the backend, update `API_PREFIX` there too.
