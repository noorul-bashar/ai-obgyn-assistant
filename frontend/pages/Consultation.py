"""
Consultation — the front end for POST /api/v1/chat/.

Sends a clinician's free-text question (with an optional active patient_id),
retrieves relevant data from Pinecone vector database + relational DB patient history,
and renders the guarded answer from the LLM decision chain with sources and guardrails.
"""
import streamlit as st
from api_client import APIError
from utils import (
    PAGE_HISTORY,
    PAGE_PATIENTS,
    get_client,
    init_session_state,
    inject_css,
    render_disclaimer_banner,
    render_sidebar,
)

st.set_page_config(page_title="Consultation · AI OB-GYN Assistant", page_icon="💬", layout="wide")

init_session_state()
inject_css()
render_sidebar()

st.title("💬 Consultation")
st.caption(
    "Ask a clinical question. The backend retrieves relevant reference material from Pinecone vector database "
    "and patient history from the database (if present), then applies safety guardrails and synthesizes an answer via LLM."
)

patient_id = st.session_state.get("selected_patient_id")
patient_name = st.session_state.get("selected_patient_name")

# ------------------------------------------------------------------ #
# header row & patient mode context
# ------------------------------------------------------------------ #
head_left, head_right = st.columns([4, 1])
chat_key = patient_id if patient_id else "general_consultation"
st.session_state.chat_histories.setdefault(chat_key, [])

with head_left:
    if patient_id and patient_name:
        st.markdown(f"#### Consulting for **{patient_name}**")
        st.caption("Patient record active. Any queries sent will evaluate medical history recorded in the database.")
    else:
        st.markdown("#### 🌐 **General Consultation Mode**")
        st.caption("No specific patient selected. Queries will search Pinecone reference materials and send context to LLM.")

with head_right:
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat_histories[chat_key] = []
        st.rerun()

# ------------------------------------------------------------------ #
# quick patient context (if patient selected)
# ------------------------------------------------------------------ #
if patient_id:
    with st.expander("🗂️ Active patient context & history status"):
        try:
            history = get_client().get_history(patient_id)
        except APIError as exc:
            history = None
            st.caption(f"Couldn't load history: {exc.message}")

        if history is not None:
            if not history:
                st.info("No prior visits on record for this patient. RAG pipeline will still search Pinecone vector database.", icon="ℹ️")
            else:
                st.success(f"{len(history)} visit entry/entries recorded in database.", icon="📋")
                for entry in history[:3]:
                    st.markdown(
                        f"**{entry['visit_date'][:10]}** — {entry['chief_complaint']}  \n"
                        f"<span class='obgyn-muted'>Diagnosis: {entry.get('diagnosis') or 'n/a'} · "
                        f"Treatment: {entry.get('treatment_plan') or 'n/a'}</span>",
                        unsafe_allow_html=True,
                    )
                if len(history) > 3:
                    st.caption(f"+ {len(history) - 3} more visit(s).")
            st.page_link(PAGE_HISTORY, label="Open full history", icon="📖")
else:
    st.info(
        "You are currently in **General Mode**. You can send clinical queries without selecting a patient. "
        "To link a query to a specific patient, select or add a patient on the Patients page.",
        icon="💡"
    )
    if st.button("🧑‍⚕️ Select or Add Patient →"):
        st.switch_page(PAGE_PATIENTS)

st.divider()

# ------------------------------------------------------------------ #
# message rendering
# ------------------------------------------------------------------ #
def render_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg.get("error"):
            st.error(msg["content"], icon="🚫")
            return

        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            render_disclaimer_banner(msg.get("disclaimer", ""), msg.get("escalate", False))

            if msg.get("used_history"):
                badge = "📋 Patient history was retrieved from database and included in prompt"
            elif patient_id:
                badge = "📋 No prior patient history was found in database for this query"
            else:
                badge = "🌐 General consultation (No patient history used)"
            st.caption(badge)

            sources = msg.get("sources") or []
            if sources:
                with st.expander(f"📚 Pinecone Retrieved Sources ({len(sources)})"):
                    for s in sources:
                        score = s.get("relevance_score")
                        score_label = f"{score:.2f}" if isinstance(score, (int, float)) else "n/a"
                        st.markdown(f"**{s.get('document_id', 'unknown document')}** · relevance {score_label}")
                        st.caption(s.get("snippet", ""))
                        st.markdown("---")

for msg in st.session_state.chat_histories[chat_key]:
    render_message(msg)

if not st.session_state.chat_histories[chat_key]:
    st.info("Ask any clinical query — e.g. guideline lookups, symptom triage, or risk factor assessment.", icon="💡")

# ------------------------------------------------------------------ #
# quick-action suggestions
# ------------------------------------------------------------------ #
if patient_id:
    suggestions = [
        "Summarize this patient's history and any relevant risk factors.",
        "What follow-up questions should I ask this patient?",
        "What do current guidelines say about this patient's chief complaint?",
    ]
else:
    suggestions = [
        "What are the diagnostic criteria for preeclampsia with severe features?",
        "What is the first-line treatment for post-partum hemorrhage?",
        "Summarize ACOG guidelines for gestational diabetes screening.",
    ]

sug_cols = st.columns(len(suggestions))
for col, text in zip(sug_cols, suggestions):
    if col.button(text, use_container_width=True, key=f"sugg_{hash(text)}"):
        st.session_state.pending_message = text
        st.rerun()

# ------------------------------------------------------------------ #
# input handling
# ------------------------------------------------------------------ #
incoming = st.session_state.pop("pending_message", None)
typed = st.chat_input("Ask a clinical question...")
if typed:
    incoming = typed

if incoming:
    st.session_state.chat_histories[chat_key].append({"role": "user", "content": incoming})
    try:
        with st.spinner("Retrieving data from Pinecone vector database & consulting LLM..."):
            result = get_client().send_chat(patient_id, incoming)
        st.session_state.chat_histories[chat_key].append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result.get("sources", []),
                "disclaimer": result.get("disclaimer", ""),
                "escalate": result.get("escalate_to_clinician", False),
                "used_history": result.get("used_patient_history", False),
            }
        )
    except APIError as exc:
        st.session_state.chat_histories[chat_key].append(
            {"role": "assistant", "error": True, "content": exc.message}
        )
    st.rerun()
