"""
Creates all tables from the SQLAlchemy models.

For production, use Alembic migrations instead (`alembic upgrade head`) so
schema changes are versioned — this script is a quick-start for local dev.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.db.base_class import Base  # noqa: E402
from app.db.models import IngestedDocument, MedicalHistory, Patient  # noqa: E402, F401
from app.db.session import engine  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()
