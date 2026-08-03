"""
AI OB-GYN Clinical Assistant — Streamlit front end.

Run with:
    streamlit run streamlit_app.py

Talks to the FastAPI backend in ../app over HTTP (see api_client.py). No
backend code is imported directly — this is a standalone client, exactly
like any other consumer of the API.
"""
import streamlit as st
from api_client import APIError
from utils import (
    PAGE_CONSULTATION,
    PAGE_DOCUMENTS,
    PAGE_HISTORY,
    PAGE_PATIENTS,
    get_client,
    init_session_state,
    inject_css,
    render_sidebar,
)

st.set_page_config(
    page_title="AI OB-GYN Clinical Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()
inject_css()
render_sidebar()

st.title("🩺 AI OB-GYN Clinical Assistant")
st.caption("Decision support for OB-GYN care — combines patient history with a RAG pipeline over clinical reference material.")

st.markdown(
    '<div class="obgyn-banner obgyn-banner-standard">ℹ️&nbsp; '
    "This tool produces <strong>AI-generated decision support for clinician review</strong> — "
    "it is not an autonomous diagnostic tool and does not replace an in-person evaluation. "
    "Every answer in the Consultation tab carries its own disclaimer from the backend, and "
    "urgent-sounding queries are flagged for escalation."
    "</div>",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------- #
# status + quick stats
# ---------------------------------------------------------------------- #
col_status, col_patients, col_docs = st.columns(3)

with col_status:
    st.markdown("##### Backend status")
    status = st.session_state.backend_status
    if status == "ok":
        st.success(f"Reachable at\n\n`{st.session_state.base_url}`", icon="✅")
    elif status == "error":
        st.error("Unreachable — check the sidebar", icon="🚫")
    else:
        st.info("Not checked yet", icon="❔")

with col_patients:
    st.markdown("##### Patients on record")
    if st.session_state.backend_status == "ok":
        try:
            client = get_client()
            patients = client.list_patients(skip=0, limit=100)
            st.session_state.patients_cache = patients
            count_label = "100+" if len(patients) == 100 else str(len(patients))
            st.metric("Patients", count_label, label_visibility="collapsed")
            st.caption(f"{count_label} patient(s) registered")
        except APIError as exc:
            st.caption(f"Couldn't load: {exc.message}")
    else:
        st.caption("Connect to the backend to see this.")

with col_docs:
    st.markdown("##### Knowledge base")
    st.caption(
        "The backend has no endpoint to list ingested documents — use the "
        "Documents tab to upload new reference material or patient records."
    )

st.divider()

# ---------------------------------------------------------------------- #
# navigation
# ---------------------------------------------------------------------- #
st.markdown("##### Get started")
nav1, nav2, nav3, nav4 = st.columns(4)

with nav1, st.container(border=True):
    st.markdown("**💬 Consultation**")
    st.caption("Ask a clinical question for the active patient and get a guarded, sourced answer.")
    st.page_link(PAGE_CONSULTATION, label="Open", icon="➡️")

with nav2, st.container(border=True):
    st.markdown("**🧑‍⚕️ Patients**")
    st.caption("Create, search, edit, and delete patient records.")
    st.page_link(PAGE_PATIENTS, label="Open", icon="➡️")

with nav3, st.container(border=True):
    st.markdown("**📖 Medical History**")
    st.caption("Review or add visit records for a patient.")
    st.page_link(PAGE_HISTORY, label="Open", icon="➡️")

with nav4, st.container(border=True):
    st.markdown("**📄 Documents**")
    st.caption("Ingest clinical guidelines or patient-specific scans into the knowledge base.")
    st.page_link(PAGE_DOCUMENTS, label="Open", icon="➡️")

if st.session_state.backend_status != "ok":
    st.divider()
    st.warning(
        "The sidebar shows the backend as unreachable or not yet checked. Start it with "
        "`uvicorn app.main:app --reload` (and make sure Postgres is running), then click "
        "**Test connection** in the sidebar.",
        icon="⚠️",
    )
