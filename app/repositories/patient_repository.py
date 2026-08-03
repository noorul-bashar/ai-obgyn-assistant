import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def create_patient(db: Session, data: PatientCreate) -> Patient:
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patient(db: Session, patient_id: uuid.UUID) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found")
    return patient


def list_patients(db: Session, skip: int = 0, limit: int = 100) -> list[Patient]:
    return db.query(Patient).offset(skip).limit(limit).all()


def update_patient(db: Session, patient_id: uuid.UUID, data: PatientUpdate) -> Patient:
    patient = get_patient(db, patient_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient_id: uuid.UUID) -> None:
    """
    Hard-deletes a patient and (via cascade) their history.
    Needed for data-subject deletion / "right to be forgotten" requests —
    keep an audit log of *that a deletion happened* somewhere outside this
    table if your compliance regime requires one.
    """
    patient = get_patient(db, patient_id)
    db.delete(patient)
    db.commit()
