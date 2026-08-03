import datetime

import pytest


@pytest.fixture
def sample_history_entries():
    """Lightweight stand-in for MedicalHistory rows, used where the full
    ORM/DB isn't needed (keeps unit tests fast and DB-free)."""

    class FakeEntry:
        def __init__(self, visit_date, chief_complaint, diagnosis, treatment_plan):
            self.visit_date = visit_date
            self.chief_complaint = chief_complaint
            self.diagnosis = diagnosis
            self.treatment_plan = treatment_plan

    return [
        FakeEntry(datetime.datetime(2026, 3, 1), "routine checkup", "normal", "none"),
        FakeEntry(datetime.datetime(2026, 6, 10), "spotting", "subchorionic hematoma", "pelvic rest"),
    ]
