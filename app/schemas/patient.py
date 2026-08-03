import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    full_name: str
    date_of_birth: date
    contact_number: str | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = None
    contact_number: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    date_of_birth: date
    contact_number: str | None
    created_at: datetime


class MedicalHistoryCreate(BaseModel):
    chief_complaint: str
    symptoms: str | None = None
    diagnosis: str | None = None
    treatment_plan: str | None = None
    clinician_notes: str | None = None


class MedicalHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    chief_complaint: str
    symptoms: str | None
    diagnosis: str | None
    treatment_plan: str | None
    visit_date: datetime
