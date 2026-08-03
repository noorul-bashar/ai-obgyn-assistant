"""
HTTP client for the AI OB-GYN Clinical Assistant FastAPI backend.

Every method here mirrors an endpoint in the backend exactly — same path,
same payload shape, same auth header — so this file is the single place to
update if the backend's contract ever changes:

    app/api/v1/endpoints/health.py     -> health_check()
    app/api/v1/endpoints/patients.py   -> list/get/create/update/delete_patient,
                                           get_history / add_history
    app/api/v1/endpoints/chat.py       -> send_chat()
    app/api/v1/endpoints/documents.py  -> upload_document()

Auth: every route except /health requires an `X-API-Key` header
(app/core/security.py), matching the backend's API_KEY setting.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, BinaryIO

import requests

# Matches Settings.API_V1_PREFIX in app/config.py. If that's changed on the
# backend, update it here too.
API_PREFIX = "/api/v1"

DEFAULT_TIMEOUT = 30  # seconds, for ordinary CRUD calls
CHAT_TIMEOUT = 120  # chat hits retrieval + an LLM call, so give it more room
UPLOAD_TIMEOUT = 600  # document ingestion (OCR/parsing + embedding) can take longer for large PDFs

_UNSET = object()  # sentinel distinguishing "not provided" from an explicit None


class APIError(Exception):
    """
    Raised for any failed call to the backend: non-2xx responses, connection
    failures, or timeouts. `.message` is always safe to show directly to a
    clinician in the UI.
    """

    def __init__(self, message: str, status_code: int | None = None, detail: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class OBGYNClient:
    """Thin wrapper around `requests` for the OB-GYN assistant API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _url(self, path: str) -> str:
        return f"{self.base_url}{API_PREFIX}{path}"

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key}

    def _request(self, method: str, path: str, *, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
        if not self.base_url:
            raise APIError("No backend URL configured. Set it in the sidebar first.")

        try:
            resp = requests.request(
                method,
                self._url(path),
                headers=self._headers(),
                timeout=timeout,
                **kwargs,
            )
        except requests.exceptions.ConnectionError as exc:
            raise APIError(
                f"Can't reach the API at {self.base_url}{API_PREFIX}. Is the backend running "
                f"(`uvicorn app.main:app --reload`) and is the URL in the sidebar correct?"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise APIError(
                "The request timed out. The backend (or one of Pinecone/Anthropic/the DB it "
                "depends on) may be slow or unresponsive right now."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise APIError(f"Request failed: {exc}") from exc

        if resp.ok:
            return resp

        raise _to_api_error(resp)

    # ------------------------------------------------------------------ #
    # health — app/api/v1/endpoints/health.py (no auth required)
    # ------------------------------------------------------------------ #
    def health_check(self) -> dict:
        resp = self._request("GET", "/health", timeout=5)
        return resp.json()

    # ------------------------------------------------------------------ #
    # patients — app/api/v1/endpoints/patients.py
    # ------------------------------------------------------------------ #
    def list_patients(self, skip: int = 0, limit: int = 100) -> list[dict]:
        resp = self._request("GET", "/patients/", params={"skip": skip, "limit": limit})
        return resp.json()

    def get_patient(self, patient_id: str) -> dict:
        resp = self._request("GET", f"/patients/{patient_id}")
        return resp.json()

    def create_patient(
        self,
        full_name: str,
        date_of_birth: dt.date,
        contact_number: str | None = None,
    ) -> dict:
        payload = {
            "full_name": full_name,
            "date_of_birth": date_of_birth.isoformat(),
            "contact_number": contact_number or None,
        }
        resp = self._request("POST", "/patients/", json=payload)
        return resp.json()

    def update_patient(
        self,
        patient_id: str,
        full_name: str | None | object = _UNSET,
        contact_number: str | None | object = _UNSET,
    ) -> dict:
        """
        Only fields explicitly passed are sent to the backend (which uses
        Pydantic's exclude_unset, so an omitted field is left alone while an
        explicit `contact_number=None` clears it to null). Leave a
        parameter at its default to leave that field untouched.
        """
        payload: dict[str, Any] = {}
        if full_name is not _UNSET:
            payload["full_name"] = full_name
        if contact_number is not _UNSET:
            payload["contact_number"] = contact_number
        resp = self._request("PATCH", f"/patients/{patient_id}", json=payload)
        return resp.json()

    def delete_patient(self, patient_id: str) -> None:
        self._request("DELETE", f"/patients/{patient_id}")

    # ------------------------------------------------------------------ #
    # medical history — nested under /patients/{id}/history
    # ------------------------------------------------------------------ #
    def get_history(self, patient_id: str) -> list[dict]:
        resp = self._request("GET", f"/patients/{patient_id}/history")
        return resp.json()

    def add_history(
        self,
        patient_id: str,
        chief_complaint: str,
        symptoms: str | None = None,
        diagnosis: str | None = None,
        treatment_plan: str | None = None,
        clinician_notes: str | None = None,
    ) -> dict:
        payload = {
            "chief_complaint": chief_complaint,
            "symptoms": symptoms or None,
            "diagnosis": diagnosis or None,
            "treatment_plan": treatment_plan or None,
            "clinician_notes": clinician_notes or None,
        }
        resp = self._request("POST", f"/patients/{patient_id}/history", json=payload)
        return resp.json()

    # ------------------------------------------------------------------ #
    # chat — app/api/v1/endpoints/chat.py
    # ------------------------------------------------------------------ #
    def send_chat(self, patient_id: str | None, message: str) -> dict:
        payload: dict[str, Any] = {"message": message}
        if patient_id:
            payload["patient_id"] = patient_id
        resp = self._request("POST", "/chat/", json=payload, timeout=CHAT_TIMEOUT)
        return resp.json()

    # ------------------------------------------------------------------ #
    # documents — app/api/v1/endpoints/documents.py
    # ------------------------------------------------------------------ #
    def upload_document(
        self,
        filename: str,
        file_obj: BinaryIO | bytes,
        content_type: str = "application/octet-stream",
        patient_id: str | None = None,
    ) -> dict:
        files = {"file": (filename, file_obj, content_type)}
        params = {"patient_id": patient_id} if patient_id else None
        resp = self._request(
            "POST", "/documents/upload", files=files, params=params, timeout=UPLOAD_TIMEOUT
        )
        return resp.json()


# ---------------------------------------------------------------------- #
# error formatting
# ---------------------------------------------------------------------- #
def _to_api_error(resp: requests.Response) -> APIError:
    try:
        body = resp.json()
    except ValueError:
        body = None

    status_code = resp.status_code

    if status_code == 401:
        message = "Invalid or missing API key. Check the API key in the sidebar against the backend's API_KEY setting."
    elif status_code == 404:
        message = (body or {}).get("detail") if isinstance(body, dict) else None
        message = message or "The requested resource was not found."
    elif status_code == 422:
        message = _format_validation_error(body)
    elif status_code == 503:
        message = (body or {}).get("detail") if isinstance(body, dict) else None
        message = message or "The backend's knowledge base or AI service is temporarily unavailable."
    elif isinstance(body, dict) and "detail" in body:
        message = str(body["detail"])
    else:
        snippet = (resp.text or "")[:300]
        message = f"Request failed with status {status_code}." + (f" {snippet}" if snippet else "")

    return APIError(message, status_code=status_code, detail=body)


def _format_validation_error(body: Any) -> str:
    """FastAPI/Pydantic 422 bodies look like {"detail": [{"loc": [...], "msg": "...", ...}]}."""
    if isinstance(body, dict) and isinstance(body.get("detail"), list):
        parts = []
        for err in body["detail"]:
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            msg = err.get("msg", "invalid value")
            parts.append(f"{loc}: {msg}" if loc else msg)
        if parts:
            return "Please check your input — " + "; ".join(parts)
    if isinstance(body, dict) and "detail" in body:
        return f"Validation error: {body['detail']}"
    return "Validation error: the backend rejected this request."
