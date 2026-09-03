from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(128), nullable=True)
    department = db.Column(db.String(128), nullable=True)
    preferred_theme = db.Column(db.String(64), nullable=False, default="varsayilan")
    password_hash = db.Column(db.String(255), nullable=True)
    system_role = db.Column(db.String(32), nullable=False, default="user")
    must_change_password = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.text("FALSE")
    )
    employment_status = db.Column(
        db.String(16),
        nullable=False,
        default="aktif",
        server_default=db.text("'aktif'"),
    )
    termination_date = db.Column(db.Date, nullable=True)
    termination_note = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role,
            "department": self.department,
            "preferred_theme": self.preferred_theme,
            "system_role": self.system_role,
            "employment_status": self.employment_status,
            "termination_date": (
                self.termination_date.isoformat() if self.termination_date else None
            ),
            "termination_note": self.termination_note,
        }


class LdapProfile(db.Model):
    __tablename__ = "ldap_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    host = db.Column(db.String(256), nullable=False)
    port = db.Column(db.Integer, nullable=False, default=389)
    base_dn = db.Column(db.String(256), nullable=False)
    bind_dn = db.Column(db.String(256), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "base_dn": self.base_dn,
            "bind_dn": self.bind_dn,
        }
