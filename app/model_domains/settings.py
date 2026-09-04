from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB

from .base import db


class SettingList(db.Model):
    __tablename__ = "setting_lists"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), nullable=False, unique=True, index=True)
    label = db.Column(db.String(160), nullable=False)
    scope = db.Column(db.String(64), nullable=False, default="general", index=True)
    description = db.Column(db.String(500))
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    options = db.relationship(
        "SettingOption",
        back_populates="setting_list",
        cascade="all, delete-orphan",
        order_by="SettingOption.sort_order, SettingOption.id",
    )


class SettingOption(db.Model):
    __tablename__ = "setting_options"
    __table_args__ = (
        db.UniqueConstraint("setting_list_id", "value", name="uq_setting_option_list_value"),
    )

    id = db.Column(db.Integer, primary_key=True)
    setting_list_id = db.Column(db.Integer, db.ForeignKey("setting_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(160), nullable=False)
    value = db.Column(db.String(160), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    setting_list = db.relationship("SettingList", back_populates="options")


class FieldGroup(db.Model):
    __tablename__ = "field_groups"
    __table_args__ = (db.UniqueConstraint("entity_type", "key", name="uq_field_group_entity_key"),)

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(64), nullable=False, index=True)
    key = db.Column(db.String(128), nullable=False)
    label = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(500))
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    fields = db.relationship("CustomField", back_populates="group", order_by="CustomField.sort_order, CustomField.id")


class CustomField(db.Model):
    __tablename__ = "custom_fields"
    __table_args__ = (db.UniqueConstraint("entity_type", "field_key", name="uq_custom_field_entity_key"),)

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(64), nullable=False, index=True)
    field_key = db.Column(db.String(128), nullable=False)
    label = db.Column(db.String(160), nullable=False)
    field_type = db.Column(db.String(32), nullable=False, default="text")
    group_id = db.Column(db.Integer, db.ForeignKey("field_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    required = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    visible_form = db.Column(db.Boolean, nullable=False, default=True)
    visible_list = db.Column(db.Boolean, nullable=False, default=False)
    searchable = db.Column(db.Boolean, nullable=False, default=False)
    sortable = db.Column(db.Boolean, nullable=False, default=False)
    placeholder = db.Column(db.String(250))
    help_text = db.Column(db.String(500))
    default_value = db.Column(db.String(500))
    validation_min = db.Column(db.Numeric)
    validation_max = db.Column(db.Numeric)
    regex_pattern = db.Column(db.String(500))
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    settings_json = db.Column(JSONB, nullable=False, default=dict)
    depends_on_field_id = db.Column(db.Integer, db.ForeignKey("custom_fields.id", ondelete="SET NULL"), nullable=True, index=True)
    depends_on_values = db.Column(JSONB, nullable=False, default=list)

    group = db.relationship("FieldGroup", back_populates="fields")
    options = db.relationship(
        "CustomFieldOption",
        back_populates="field",
        cascade="all, delete-orphan",
        order_by="CustomFieldOption.sort_order, CustomFieldOption.id",
    )


class CustomFieldOption(db.Model):
    __tablename__ = "custom_field_options"
    __table_args__ = (db.UniqueConstraint("field_id", "value", name="uq_custom_field_option_value"),)

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey("custom_fields.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(160), nullable=False)
    value = db.Column(db.String(160), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    field = db.relationship("CustomField", back_populates="options")


class CustomFieldValue(db.Model):
    __tablename__ = "custom_field_values"
    __table_args__ = (
        db.UniqueConstraint("field_id", "entity_type", "entity_id", name="uq_custom_field_value_target"),
        db.Index("ix_custom_field_values_target", "entity_type", "entity_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey("custom_fields.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = db.Column(db.String(64), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    value_text = db.Column(db.Text)
    value_number = db.Column(db.Numeric)
    value_date = db.Column(db.DateTime)
    value_boolean = db.Column(db.Boolean)
    value_json = db.Column(JSONB)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    field = db.relationship("CustomField")


class DashboardWidget(db.Model):
    __tablename__ = "dashboard_widgets"

    id = db.Column(db.Integer, primary_key=True)
    widget_key = db.Column(db.String(128), nullable=False, unique=True)
    label = db.Column(db.String(160), nullable=False)
    widget_type = db.Column(db.String(32), nullable=False, default="metric")
    config_json = db.Column(JSONB, nullable=False, default=dict)
    active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


def custom_value_as_python(value: CustomFieldValue) -> Any:
    if value.value_json is not None:
        return value.value_json
    if value.value_boolean is not None:
        return value.value_boolean
    if value.value_date is not None:
        return value.value_date
    if value.value_number is not None:
        return value.value_number
    return value.value_text
