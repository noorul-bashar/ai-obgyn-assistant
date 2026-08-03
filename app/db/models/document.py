import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentSourceType(str, enum.Enum):
    PDF = "pdf"
    IMAGE = "image"


class IngestedDocument(Base):
    """
    Tracks a source file (PDF/image) that has gone through the ingestion
    pipeline: load -> clean -> chunk -> embed -> upsert into the vector DB.
    """

    __tablename__ = "ingested_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Null patient_id => general clinical knowledge (guidelines, literature).
    # Set patient_id => patient-specific scanned record.
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=True
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[DocumentSourceType] = mapped_column(Enum(DocumentSourceType), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.PENDING)

    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
