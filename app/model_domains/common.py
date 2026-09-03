from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db

def find_existing_by_name(model: type[NamedEntityMixin], name: str):
    normalized = name.strip()
    if not normalized:
        return None
    return model.query.filter(func.lower(model.name) == normalized.lower()).first()


