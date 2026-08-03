"""
Patients — front end for the /patients CRUD endpoints.
"""
import datetime as dt

import streamlit as st
from api_client import APIError
from utils import (
    PAGE_CONSULTATION,
    PAGE_HISTORY,
    calculate_age,
    get_client,
    init_session_state,
    inject_css,
    render_sidebar,
    set_active_patient,
)

st.set_page_config(page_title="Patients · AI OB-GYN Assistant", page_icon="🧑‍⚕️", layout="wide")

init_session_state()
inject_css()
render_sidebar()

st.title("🧑‍⚕️ Patients")
st.caption(
    "Create and manage patient records. Deleting a patient is a permanent hard delete of "
    "the patient and all of their medical history — there's no undo."
)

if "patients_skip" not in st.session_state:
    st.session_state.patients_skip = 0
if "patients_page_size" not in st.session_state:
    st.session_state.patients_page_size = 25


# ------------------------------------------------------------------ #
# helpers
# ------------------------------------------------------------------ #
def render_edit_form(patient: dict) -> None:
    pid = patient["id"]
    with st.form(f"edit_form_{pid}"):
        new_name = st.text_input("Full name", value=patient["full_name"])
        new_contact = st.text_input("Contact number", value=patient.get("contact_number") or "")
        c1, c2 = st.columns(2)
        save = c1.form_submit_button("💾 Save", type="primary", use_container_width=True)
        cancel = c2.form_submit_button("Cancel", use_container_width=True)

    if save:
        if not new_name.strip():
            st.error("Full name can't be empty.")
            return
        try:
            updated = get_client().update_patient(
                pid, full_name=new_name.strip(), contact_number=(new_contact.strip() or None)
            )
            st.session_state.editing_patient_id = None
            if st.session_state.selected_patient_id == pid:
                set_active_patient(pid, updated["full_name"])
            st.success("Patient updated.")
            st.rerun()
        except APIError as exc:
            st.error(exc.message)

    if cancel:
        st.session_state.editing_patient_id = None
        st.rerun()


def render_delete_confirm(patient: dict) -> None:
    pid = patient["id"]
    st.warning(
        f"Permanently delete **{patient['full_name']}** and all of their medical history? "
        "This cannot be undone.",
        icon="⚠️",
    )
    c1, c2 = st.columns(2)
    if c1.button("Yes, permanently delete", key=f"confirm_del_{pid}", type="primary", use_container_width=True):
        try:
            get_client().delete_patient(pid)
            st.session_state.confirm_delete_patient_id = None
            if st.session_state.selected_patient_id == pid:
                st.session_state.selected_patient_id = None
                st.session_state.selected_patient_name = None
            st.session_state.chat_histories.pop(pid, None)
            st.success(f"Deleted {patient['full_name']}.")
            st.rerun()
        except APIError as exc:
            st.error(exc.message)
    if c2.button("Cancel", key=f"cancel_del_{pid}", use_container_width=True):
        st.session_state.confirm_delete_patient_id = None
        st.rerun()


def render_patient_card(patient: dict) -> None:
    pid = patient["id"]
    is_active = st.session_state.selected_patient_id == pid

    with st.container(border=True):
        top = st.columns([3, 2, 1.3])
        with top[0]:
            name_line = f"**{patient['full_name']}**" + ("  ✅ *active*" if is_active else "")
            st.markdown(name_line)
            age = calculate_age(patient["date_of_birth"])
            st.caption(
                f"DOB {patient['date_of_birth']} · Age {age} · "
                f"{patient.get('contact_number') or 'no contact on file'}"
            )
        with top[1]:
            st.caption(f"ID: `{pid}`")
            st.caption(f"Added {str(patient['created_at'])[:10]}")
        with top[2]:
            if st.button(
                "Active ✓" if is_active else "Set active",
                key=f"active_{pid}",
                disabled=is_active,
                use_container_width=True,
            ):
                set_active_patient(pid, patient["full_name"])
                st.rerun()

        btn_cols = st.columns(4)
        if btn_cols[0].button("💬 Consult", key=f"consult_{pid}", use_container_width=True):
            set_active_patient(pid, patient["full_name"])
            st.switch_page(PAGE_CONSULTATION)
        if btn_cols[1].button("📖 History", key=f"hist_{pid}", use_container_width=True):
            set_active_patient(pid, patient["full_name"])
            st.switch_page(PAGE_HISTORY)
        if btn_cols[2].button("✏️ Edit", key=f"edit_{pid}", use_container_width=True):
            st.session_state.editing_patient_id = (
                None if st.session_state.editing_patient_id == pid else pid
            )
            st.session_state.confirm_delete_patient_id = None
        if btn_cols[3].button("🗑️ Delete", key=f"del_{pid}", use_container_width=True):
            st.session_state.confirm_delete_patient_id = pid
            st.session_state.editing_patient_id = None

        if st.session_state.editing_patient_id == pid:
            render_edit_form(patient)
        if st.session_state.confirm_delete_patient_id == pid:
            render_delete_confirm(patient)


# ------------------------------------------------------------------ #
# tabs
# ------------------------------------------------------------------ #
tab_directory, tab_add = st.tabs(["📋 Directory", "➕ Add patient"])

with tab_add:
    st.subheader("Add a new patient")
    with st.form("add_patient_form", clear_on_submit=True):
        full_name = st.text_input("Full name *")
        date_of_birth = st.date_input(
            "Date of birth *",
            value=dt.date(1990, 1, 1),
            min_value=dt.date(1900, 1, 1),
            max_value=dt.date.today(),
        )
        contact_number = st.text_input("Contact number (optional)")
        submitted = st.form_submit_button("Create patient", type="primary")

    if submitted:
        if not full_name.strip():
            st.error("Full name is required.")
        else:
            try:
                patient = get_client().create_patient(
                    full_name.strip(), date_of_birth, contact_number.strip() or None
                )
                st.success(f"Created patient **{patient['full_name']}**.")
                set_active_patient(patient["id"], patient["full_name"])
                col_a, col_b = st.columns(2)
                with col_a:
                    st.page_link(PAGE_CONSULTATION, label="Start a consultation", icon="💬")
                with col_b:
                    st.page_link(PAGE_HISTORY, label="Add a history entry", icon="📖")
            except APIError as exc:
                st.error(exc.message)

with tab_directory:
    top_l, top_m, top_r = st.columns([2, 1, 1])
    with top_l:
        search = st.text_input("Search by name (current page only)", "")
    with top_m:
        size_options = [10, 25, 50, 100]
        page_size = st.selectbox(
            "Page size", size_options, index=size_options.index(st.session_state.patients_page_size)
        )
        if page_size != st.session_state.patients_page_size:
            st.session_state.patients_page_size = page_size
            st.session_state.patients_skip = 0
            st.rerun()
    with top_r:
        st.write("")
        st.write("")
        # No explicit handler needed: clicking this reruns the script, which
        # always fetches a fresh page of patients below.
        st.button("🔄 Refresh", use_container_width=True)

    try:
        raw_patients = get_client().list_patients(
            skip=st.session_state.patients_skip, limit=st.session_state.patients_page_size
        )
    except APIError as exc:
        st.error(exc.message)
        raw_patients = []

    patients = raw_patients
    if search.strip():
        needle = search.strip().lower()
        patients = [p for p in raw_patients if needle in p["full_name"].lower()]

    if not raw_patients and st.session_state.patients_skip == 0:
        st.info("No patients yet — add one in the **Add patient** tab.", icon="👤")
    elif not patients:
        st.info("No patients on this page match that search.", icon="🔍")
    else:
        for p in patients:
            render_patient_card(p)

    nav_l, nav_mid, nav_r = st.columns([1, 2, 1])
    with nav_l:
        if st.button("⬅️ Previous", disabled=st.session_state.patients_skip == 0, use_container_width=True):
            st.session_state.patients_skip = max(
                0, st.session_state.patients_skip - st.session_state.patients_page_size
            )
            st.rerun()
    with nav_mid:
        start = st.session_state.patients_skip + 1 if raw_patients else 0
        end = st.session_state.patients_skip + len(raw_patients)
        st.caption(f"Showing {start}–{end}" if raw_patients else "No results")
    with nav_r:
        has_more = len(raw_patients) == st.session_state.patients_page_size
        if st.button("Next ➡️", disabled=not has_more, use_container_width=True):
            st.session_state.patients_skip += st.session_state.patients_page_size
            st.rerun()
