import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.history import MedicalHistory
from app.schemas.patient import MedicalHistoryCreate


def add_history_entry(db: Session, patient_id: uuid.UUID, data: MedicalHistoryCreate) -> MedicalHistory:
    entry = MedicalHistory(patient_id=patient_id, **data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_history_for_patient(
    db: Session, patient_id: uuid.UUID, limit: int = 20
) -> list[MedicalHistory]:
    return (
        db.query(MedicalHistory)
        .filter(MedicalHistory.patient_id == patient_id)
        .order_by(desc(MedicalHistory.visit_date))
        .limit(limit)
        .all()
    )


def summarize_history(history_entries: list[MedicalHistory]) -> str:
    """
    Turns structured history rows into a compact text block the LLM can use
    as context. Keeping this separate from the DB layer means the prompt
    format can change without touching persistence code.
    """
    if not history_entries:
        return "No prior visits on record."

    lines = []
    for entry in history_entries:
        lines.append(
            f"- {entry.visit_date.date()}: complaint='{entry.chief_complaint}', "
            f"diagnosis='{entry.diagnosis or 'n/a'}', "
            f"treatment='{entry.treatment_plan or 'n/a'}'"
        )
    return "\n".join(lines)
