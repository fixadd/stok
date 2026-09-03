from __future__ import annotations

from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class NamedEntityMixin:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}

