"""
Documents — front end for POST /api/v1/documents/upload.

Note: the backend has no endpoint to list previously ingested documents, so
this page can only show what's been uploaded during the current browser
session, not the full ingestion history.
"""
import streamlit as st
from api_client import APIError
from utils import (
    get_client,
    init_session_state,
    inject_css,
    render_patient_selector,
    render_sidebar,
    status_pill,
)

st.set_page_config(page_title="Documents · AI OB-GYN Assistant", page_icon="📄", layout="wide")

init_session_state()
inject_css()
render_sidebar()

st.title("📄 Documents")
st.caption(
    "Ingest a PDF or scanned image into the knowledge base: load → clean → chunk → "
    "embed → upsert into the vector store. This runs synchronously, so larger files "
    "can take a little while."
)

if "session_uploads" not in st.session_state:
    st.session_state.session_uploads = []

SUPPORTED_TYPES = ["pdf", "png", "jpg", "jpeg", "tiff", "bmp"]

scope = st.radio(
    "What kind of document is this?",
    ["General clinical reference material", "Patient-specific record"],
    horizontal=True,
)

patient_id = None
patient_name = None
if scope == "Patient-specific record":
    selection = render_patient_selector(key="documents_patient_selector")
    if selection:
        patient_id, patient_name = selection

with st.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader(
        "Choose a file", type=SUPPORTED_TYPES, accept_multiple_files=False
    )
    submitted = st.form_submit_button("Upload and ingest", type="primary")

if submitted:
    if uploaded_file is None:
        st.error("Choose a file first.")
    elif scope == "Patient-specific record" and not patient_id:
        st.error("Select a patient for a patient-specific record, or switch to general reference material.")
    else:
        try:
            with st.spinner(f"Ingesting {uploaded_file.name}... this can take a minute for larger files."):
                result = get_client().upload_document(
                    filename=uploaded_file.name,
                    file_obj=uploaded_file.getvalue(),
                    content_type=uploaded_file.type or "application/octet-stream",
                    patient_id=patient_id,
                )
            result["_linked_patient"] = patient_name
            st.session_state.session_uploads.insert(0, result)

            if result.get("status") == "completed":
                st.success(
                    f"**{result['filename']}** ingested — {result.get('chunk_count', 0)} chunk(s) "
                    "added to the knowledge base."
                )
            elif result.get("status") == "failed":
                error_message = result.get("error_message") or "No detailed error was returned by the backend."
                st.error(
                    f"**{result['filename']}** failed to ingest: {error_message}"
                )
            else:
                st.info(f"**{result['filename']}** is {result.get('status', 'processing')}.")
        except APIError as exc:
            st.error(exc.message)

st.divider()
st.markdown("##### This session's uploads")
st.caption(
    "Local to this browser session only — the backend doesn't expose an endpoint to list "
    "all previously ingested documents."
)

if not st.session_state.session_uploads:
    st.caption("Nothing uploaded yet.")
else:
    for doc in st.session_state.session_uploads:
        with st.container(border=True):
            cols = st.columns([3, 1.5, 1.5, 1.5])
            with cols[0]:
                st.markdown(f"**{doc['filename']}**")
                if doc.get("_linked_patient"):
                    st.caption(f"Linked to {doc['_linked_patient']}")
                else:
                    st.caption("General reference material")
            with cols[1]:
                st.caption("Source type")
                st.write(doc.get("source_type", "—"))
            with cols[2]:
                st.caption("Status")
                st.markdown(status_pill(doc.get("status", "unknown")), unsafe_allow_html=True)
            with cols[3]:
                st.caption("Chunks")
                st.write(doc.get("chunk_count", 0))
