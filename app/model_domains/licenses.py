from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class LicenseName(NamedEntityMixin, db.Model):
    __tablename__ = "license_names"


