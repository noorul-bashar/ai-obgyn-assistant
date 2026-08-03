"""
Standalone CLI for bulk-ingesting a folder of PDFs/images into the vector
store, independent of the running API process.

Usage:
    python scripts/ingest_documents.py --folder ./data/clinical_guidelines
    python scripts/ingest_documents.py --folder ./data/patient_scans/some_id --patient-id <uuid>
"""
import argparse
import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.services.ingestion.pipeline import IngestionPipeline  # noqa: E402

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-ingest documents into the vector store.")
    parser.add_argument("--folder", required=True, help="Folder containing PDFs/images to ingest")
    parser.add_argument("--patient-id", required=False, help="Attach ingested docs to this patient")
    args = parser.parse_args()

    folder = Path(args.folder)
    patient_id = uuid.UUID(args.patient_id) if args.patient_id else None
    pipeline = IngestionPipeline()

    files = [p for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES]
    if not files:
        print(f"No supported files found in {folder}")
        return

    db = SessionLocal()
    try:
        for file_path in files:
            result = pipeline.run(db, file_path, patient_id=patient_id)
            print(f"{file_path.name}: {result.status.value} ({result.chunk_count} chunks)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
