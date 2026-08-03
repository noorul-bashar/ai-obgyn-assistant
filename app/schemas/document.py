import uuid

from pydantic import BaseModel, ConfigDict

from app.db.models.document import DocumentSourceType, DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    source_type: DocumentSourceType
    status: DocumentStatus
    chunk_count: int
    error_message: str | None = None
