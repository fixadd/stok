from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import func

from .base import db, NamedEntityMixin

class InfoCategory(NamedEntityMixin, db.Model):
    __tablename__ = "info_categories"


class InfoEntry(db.Model):
    __tablename__ = "info_entries"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("info_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    category = db.relationship("InfoCategory")
    attachments = db.relationship(
        "InfoAttachment",
        cascade="all, delete-orphan",
        back_populates="entry",
        order_by="InfoAttachment.uploaded_at",
    )

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.name if self.category else None,
            "created_at": self.created_at,
        }

    def to_detail_dict(self) -> dict:
        payload = self.to_summary_dict()
        payload.update(
            {
                "content": self.content,
                "image_filename": self.image_filename,
                "updated_at": self.updated_at,
            }
        )
        return payload


class InfoAttachment(db.Model):
    __tablename__ = "info_attachments"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(
        db.Integer,
        db.ForeignKey("info_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=True)
    content_type = db.Column(db.String(128), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    entry = db.relationship("InfoEntry", back_populates="attachments")


