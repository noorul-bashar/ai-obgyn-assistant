import shutil
import tempfile
import uuid
from functools import lru_cache
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.session import get_db
from app.schemas.document import DocumentOut
from app.services.ingestion.pipeline import IngestionPipeline

router = APIRouter(dependencies=[Depends(verify_api_key)])
logger = logging.getLogger(__name__)


@lru_cache
def get_ingestion_pipeline() -> IngestionPipeline:
    try:
        return IngestionPipeline()
    except RuntimeError as exc:
        logger.exception("Document ingestion pipeline is unavailable")
        raise HTTPException(
            status_code=503,
            detail=f"Document ingestion is unavailable: {exc}",
        ) from exc


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile,
    patient_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
):
    """
    Ingests a PDF or scanned image: load -> clean -> chunk -> embed -> upsert
    into Pinecone. Leave patient_id empty for general clinical reference
    material; set it for a patient-specific scanned record.

    For large files/high volume, move this to a background task queue (e.g.
    Celery/RQ) instead of running inline on the request.
    """
    filename = Path(file.filename or "upload").name
    if not filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        raise HTTPException(status_code=422, detail="Unsupported document type.")

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / filename
            with tmp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return pipeline.run(db, tmp_path, patient_id=patient_id)
    except OSError as exc:
        logger.exception("Could not save uploaded document %s", filename)
        raise HTTPException(status_code=500, detail=f"Could not save uploaded document: {exc}") from exc
