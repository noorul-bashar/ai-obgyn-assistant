"""
Shared session-state setup and small UI building blocks used by every page.

Kept separate from api_client.py so that module can stay a pure HTTP client
with no Streamlit dependency (easier to unit test on its own).
"""
from __future__ import annotations

import datetime as dt
import os

import streamlit as st
from api_client import APIError, OBGYNClient

DEFAULT_BASE_URL = os.environ.get("OBGYN_API_BASE_URL", "http://localhost:8000")
DEFAULT_API_KEY = os.environ.get("OBGYN_API_KEY", "change-me")

PAGE_CONSULTATION = "pages/Consultation.py"
PAGE_PATIENTS = "pages/Patients.py"
PAGE_HISTORY = "pages/Medical_History.py"
PAGE_DOCUMENTS = "pages/Documents.py"

_CUSTOM_CSS = """
<style>
    .block-container { padding-top: 2rem; }

    .obgyn-banner {
        padding: 0.9rem 1.1rem;
        border-radius: 0.6rem;
        border: 1px solid;
        margin-bottom: 0.9rem;
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .obgyn-banner-standard {
        background-color: #F0F7F7;
        border-color: #BFDBDB;
        color: #0F4C4E;
    }
    .obgyn-banner-escalate {
        background-color: #FDF0F0;
        border-color: #F3B9B9;
        color: #7A1E1E;
        font-weight: 500;
    }
    .obgyn-pill {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .pill-completed { background-color: #E3F3E1; color: #1E6B32; }
    .pill-processing { background-color: #FFF4DA; color: #8A5A00; }
    .pill-pending { background-color: #EDEFF2; color: #4B5563; }
    .pill-failed { background-color: #FBE2E2; color: #932020; }

    .obgyn-card {
        border: 1px solid #E4E9EA;
        border-radius: 0.6rem;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.7rem;
        background-color: #FFFFFF;
    }
    .obgyn-muted { color: #64748B; font-size: 0.85rem; }
</style>
"""


def init_session_state() -> None:
    defaults = {
        "base_url": DEFAULT_BASE_URL,
        "api_key": DEFAULT_API_KEY,
        "selected_patient_id": None,
        "selected_patient_name": None,
        "chat_histories": {},  # patient_id -> list[dict(role, content, ...)]
        "backend_status": None,  # None (untested) | "ok" | "error"
        "backend_status_detail": None,
        "patients_cache": None,  # last fetched list, so pages can reuse it without refetching
        "confirm_delete_patient_id": None,
        "editing_patient_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css() -> None:
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


def get_client() -> OBGYNClient:
    return OBGYNClient(st.session_state.base_url, st.session_state.api_key)


def check_backend(show_spinner: bool = False) -> None:
    """Pings /health and stashes the result in session_state for the sidebar indicator."""
    client = get_client()
    try:
        if show_spinner:
            with st.spinner("Checking connection..."):
                client.health_check()
        else:
            client.health_check()
        st.session_state.backend_status = "ok"
        st.session_state.backend_status_detail = None
    except APIError as exc:
        st.session_state.backend_status = "error"
        st.session_state.backend_status_detail = exc.message


def render_sidebar() -> None:
    """
    Connection settings + live status + active-patient context.
    Call once at the top of every page (including the home page).
    """
    with st.sidebar:
        st.markdown("### ⚙️ Backend connection")
        base_url = st.text_input(
            "Backend URL",
            value=st.session_state.base_url,
            help="Root URL of the FastAPI backend, e.g. http://localhost:8000 — "
            "the /api/v1 prefix is added automatically.",
        )
        api_key = st.text_input(
            "API key",
            value=st.session_state.api_key,
            type="password",
            help="Sent as the X-API-Key header. Must match API_KEY in the backend's .env.",
        )
        if base_url != st.session_state.base_url or api_key != st.session_state.api_key:
            st.session_state.base_url = base_url
            st.session_state.api_key = api_key
            st.session_state.backend_status = None  # force a re-check on next action

        if st.button("Test connection", use_container_width=True):
            check_backend(show_spinner=True)
        if st.session_state.backend_status is None:
            check_backend()

        status = st.session_state.backend_status
        if status == "ok":
            st.success("Connected", icon="✅")
        elif status == "error":
            st.error("Unreachable", icon="🚫")
            with st.expander("Details"):
                st.caption(st.session_state.backend_status_detail)

        st.divider()
        st.markdown("### 🧑‍⚕️ Active patient")
        if st.session_state.selected_patient_id:
            st.info(f"**{st.session_state.selected_patient_name}**", icon="👤")
            if st.button("Change patient", use_container_width=True):
                st.session_state.selected_patient_id = None
                st.session_state.selected_patient_name = None
                st.rerun()
        else:
            st.caption("No patient selected yet.")
            if st.button("Select or add a patient →", use_container_width=True):
                st.switch_page(PAGE_PATIENTS)

        st.divider()
        st.caption(
            "AI-generated decision support for clinician review — not an autonomous "
            "diagnostic tool. Always verify against current clinical guidelines."
        )


def set_active_patient(patient_id: str, full_name: str) -> None:
    st.session_state.selected_patient_id = patient_id
    st.session_state.selected_patient_name = full_name


def patient_options(patients: list[dict]) -> dict[str, str]:
    """id -> 'Name (DOB)' label, for selectboxes."""
    return {p["id"]: f"{p['full_name']} — DOB {p['date_of_birth']}" for p in patients}


def require_active_patient(redirect_hint: bool = True) -> tuple[str, str] | None:
    """
    Call at the top of pages that need a selected patient. Returns
    (patient_id, patient_name) if one is active, otherwise renders a prompt
    and returns None so the caller can `return` early.
    """
    pid = st.session_state.selected_patient_id
    name = st.session_state.selected_patient_name
    if pid and name:
        return pid, name

    st.info("Select a patient to get started.", icon="👤")
    if redirect_hint and st.button("Go to patients →"):
        st.switch_page(PAGE_PATIENTS)
    return None


def render_patient_selector(key: str = "patient_selector") -> tuple[str, str] | None:
    """
    Selectbox of patients, defaulting to the currently active one. Updates
    the active patient on change. Returns (id, name), or None (after
    rendering a prompt) if there are no patients yet or the fetch failed.
    """
    try:
        patients = get_client().list_patients(skip=0, limit=100)
    except APIError as exc:
        st.error(f"Couldn't load patients: {exc.message}")
        return None

    if not patients:
        st.info("No patients yet — add one on the Patients page first.", icon="👤")
        if st.button("Go to Patients →", key=f"{key}_goto"):
            st.switch_page(PAGE_PATIENTS)
        return None

    labels = patient_options(patients)
    ids = list(labels.keys())
    current = st.session_state.selected_patient_id
    index = ids.index(current) if current in ids else 0

    chosen_id = st.selectbox(
        "Patient", options=ids, index=index, format_func=lambda pid: labels[pid], key=key
    )
    chosen_name = next(p["full_name"] for p in patients if p["id"] == chosen_id)
    if chosen_id != current:
        set_active_patient(chosen_id, chosen_name)
        st.rerun()
    return chosen_id, chosen_name


def render_disclaimer_banner(text: str, escalate: bool) -> None:
    css_class = "obgyn-banner-escalate" if escalate else "obgyn-banner-standard"
    icon = "🚨" if escalate else "ℹ️"
    st.markdown(
        f'<div class="obgyn-banner {css_class}">{icon}&nbsp; {text}</div>',
        unsafe_allow_html=True,
    )


def status_pill(status: str) -> str:
    status = (status or "").lower()
    label = status.capitalize() or "Unknown"
    return f'<span class="obgyn-pill pill-{status}">{label}</span>'


def calculate_age(date_of_birth: str | dt.date) -> int:
    if isinstance(date_of_birth, str):
        date_of_birth = dt.date.fromisoformat(date_of_birth)
    today = dt.date.today()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def relative_time(timestamp: str) -> str:
    """'3 days ago' style formatting for an ISO timestamp string."""
    try:
        ts = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return timestamp

    now = dt.datetime.now(ts.tzinfo) if ts.tzinfo else dt.datetime.now()
    delta = now - ts
    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds // 86400)
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    return ts.strftime("%b %d, %Y")
