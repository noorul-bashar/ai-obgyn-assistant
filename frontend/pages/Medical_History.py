"""
Medical History — front end for GET/POST /api/v1/patients/{id}/history.
"""
import streamlit as st
from api_client import APIError
from utils import (
    get_client,
    init_session_state,
    inject_css,
    relative_time,
    render_patient_selector,
    render_sidebar,
)

st.set_page_config(page_title="Medical History · AI OB-GYN Assistant", page_icon="📖", layout="wide")

init_session_state()
inject_css()
render_sidebar()

st.title("📖 Medical History")
st.caption("View past visits or add a new visit entry for a patient.")

selection = render_patient_selector(key="history_patient_selector")
if not selection:
    st.stop()

patient_id, patient_name = selection
st.markdown(f"#### {patient_name}")

tab_timeline, tab_add = st.tabs(["🗓️ Timeline", "➕ Add visit"])

with tab_timeline:
    try:
        entries = get_client().get_history(patient_id)
    except APIError as exc:
        st.error(exc.message)
        entries = []

    if not entries:
        st.info("No visits recorded yet for this patient.", icon="🗓️")
    else:
        st.caption(f"{len(entries)} visit(s), most recent first.")
        for i, entry in enumerate(entries):
            visit_date = str(entry["visit_date"])
            title = f"{visit_date[:10]} · {entry['chief_complaint']}"
            with st.expander(title, expanded=(i == 0)):
                st.caption(relative_time(visit_date))
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Symptoms**")
                    st.write(entry.get("symptoms") or "—")
                    st.markdown("**Diagnosis**")
                    st.write(entry.get("diagnosis") or "—")
                with c2:
                    st.markdown("**Treatment plan**")
                    st.write(entry.get("treatment_plan") or "—")

with tab_add:
    st.subheader("Add a visit entry")
    with st.form("add_history_form", clear_on_submit=True):
        chief_complaint = st.text_area("Chief complaint *", height=80)
        symptoms = st.text_area("Symptoms", height=80)
        diagnosis = st.text_input("Diagnosis")
        treatment_plan = st.text_area("Treatment plan", height=80)
        clinician_notes = st.text_area(
            "Clinician notes",
            height=80,
            help="Stored on the backend, but note: the API's read endpoint doesn't return this "
            "field back, so it won't appear in the Timeline tab above.",
        )
        submitted = st.form_submit_button("Save visit entry", type="primary")

    if submitted:
        if not chief_complaint.strip():
            st.error("Chief complaint is required.")
        else:
            try:
                get_client().add_history(
                    patient_id,
                    chief_complaint=chief_complaint.strip(),
                    symptoms=symptoms.strip() or None,
                    diagnosis=diagnosis.strip() or None,
                    treatment_plan=treatment_plan.strip() or None,
                    clinician_notes=clinician_notes.strip() or None,
                )
                st.success("Visit entry saved.")
                st.rerun()
            except APIError as exc:
                st.error(exc.message)
