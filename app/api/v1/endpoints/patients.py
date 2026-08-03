import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.session import get_db
from app.repositories import history_repository, patient_repository
from app.schemas.patient import (
    MedicalHistoryCreate,
    MedicalHistoryOut,
    PatientCreate,
    PatientOut,
    PatientUpdate,
)

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    return patient_repository.create_patient(db, payload)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    return patient_repository.get_patient(db, patient_id)


@router.get("/", response_model=list[PatientOut])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return patient_repository.list_patients(db, skip, limit)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: uuid.UUID, payload: PatientUpdate, db: Session = Depends(get_db)):
    return patient_repository.update_patient(db, patient_id, payload)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    """Full data deletion — for right-to-be-forgotten / account-closure requests."""
    patient_repository.delete_patient(db, patient_id)


@router.post(
    "/{patient_id}/history", response_model=MedicalHistoryOut, status_code=status.HTTP_201_CREATED
)
def add_history(patient_id: uuid.UUID, payload: MedicalHistoryCreate, db: Session = Depends(get_db)):
    return history_repository.add_history_entry(db, patient_id, payload)


@router.get("/{patient_id}/history", response_model=list[MedicalHistoryOut])
def get_history(patient_id: uuid.UUID, db: Session = Depends(get_db)):
    return history_repository.get_history_for_patient(db, patient_id)
