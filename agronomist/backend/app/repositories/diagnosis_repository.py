from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.crop import Diagnosis


class DiagnosisRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, diagnosis: Diagnosis) -> Diagnosis:
        self.db.add(diagnosis)
        return diagnosis
