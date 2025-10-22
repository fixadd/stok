from __future__ import annotations

from datetime import datetime, timedelta
from collections import Counter
from uuid import uuid4

import shutil
import sqlite3
import tempfile

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from .models import (
    Brand,
    Factory,
    HardwareModel,
    HardwareType,
    InfoCategory,
    InfoAttachment,
    InfoEntry,
    InventoryEvent,
    InventoryItem,
    InventoryLicense,
    LdapProfile,
    LicenseName,
    ProductCatalogEntry,
    RequestGroup,
    RequestLine,
    RequestOrder,
    UsageArea,
    User,
    db,
    find_existing_by_name,
    ActivityLog,
    StockItem,
    StockLog,
)


INVENTORY_STATUSES = {"aktif", "beklemede", "arizali", "hurda", "stokta"}
DEFAULT_EVENT_ACTOR = "Sistem"
LICENSE_STATUS_LABELS = {
    "aktif": "Aktif",
    "pasif": "Pasif",
    "beklemede": "Beklemede",
}


STOCK_CATEGORY_LABELS = {
    "envanter": "Envanter",
    "cevre_birimi": "Çevre Birimi",
    "yazici": "IP Yazıcı",
    "lisans": "Lisans",
    "talep": "Talep",
    "manuel": "Manuel",
}

STOCK_STATUS_LABELS = {
    "stokta": "Stokta",
    "devredildi": "Devredildi",
    "arizali": "Arızalı",
    "hurda": "Hurda",
}

STOCK_STATUS_CLASSES = {
    "stokta": "status-stock",
    "devredildi": "status-assigned",
    "arizali": "status-faulty",
    "hurda": "status-scrap",
}

STOCK_SOURCE_LABELS = {
    "inventory": "Envanter Takip",
    "license": "Lisans Takip",
    "request": "Talep Takip",
    "manual": "Manuel Kayıt",
}


SYSTEM_ROLE_LEVELS = {
    "user": 0,
    "admin": 1,
    "superadmin": 2,
}

SYSTEM_ROLE_LABELS = {
    "user": "Kullanıcı",
    "admin": "Admin",
    "superadmin": "Süper Admin",
}


STOCK_METADATA_FIELDS: dict[str, list[dict[str, Any]]] = {
    "envanter": [
        {
            "key": "inventory_no",
            "label": "Envanter No",
            "placeholder": "ENV-001",
            "required": True,
        },
        {
            "key": "hardware_type",
            "label": "Donanım Tipi",
            "placeholder": "Örn. Dizüstü Bilgisayar",
            "required": True,
        },
        {
            "key": "brand",
            "label": "Marka",
            "placeholder": "Marka",
            "required": True,
        },
        {
            "key": "model",
            "label": "Model",
            "placeholder": "Model",
            "required": True,
        },
        {
            "key": "serial_no",
            "label": "Seri No",
            "placeholder": "Seri numarası",
            "required": False,
        },
        {
            "key": "computer_name",
            "label": "Cihaz Adı",
            "placeholder": "Örn. IT-LAPTOP-01",
            "required": False,
        },
        {
            "key": "factory",
            "label": "Fabrika",
            "placeholder": "Fabrika adı",
            "required": True,
            "assignment_only": True,
            "options_key": "factories",
        },
        {
            "key": "department",
            "label": "Departman",
            "placeholder": "Departman",
            "required": True,
            "assignment_only": True,
            "options_key": "departments",
        },
        {
            "key": "responsible",
            "label": "Sorumlu",
            "placeholder": "Sorumlu kişi",
            "required": True,
            "assignment_only": True,
            "options_key": "responsibles",
        },
        {
            "key": "ifs_no",
            "label": "IFS No",
            "placeholder": "IFS-00001",
            "required": False,
            "assignment_only": True,
        },
    ],
    "cevre_birimi": [
        {
            "key": "hardware_type",
            "label": "Donanım Tipi",
            "placeholder": "Örn. Klavye",
            "required": True,
        },
        {
            "key": "brand",
            "label": "Marka",
            "placeholder": "Marka",
            "required": False,
        },
        {
            "key": "model",
            "label": "Model",
            "placeholder": "Model",
            "required": False,
        },
        {
            "key": "serial_no",
            "label": "Seri No",
            "placeholder": "Seri numarası",
            "required": False,
        },
        {
            "key": "factory",
            "label": "Fabrika",
            "placeholder": "Fabrika adı",
            "required": False,
            "assignment_only": True,
            "options_key": "factories",
        },
        {
            "key": "department",
            "label": "Departman",
            "placeholder": "Departman",
            "required": False,
            "assignment_only": True,
            "options_key": "departments",
        },
        {
            "key": "responsible",
            "label": "Sorumlu",
            "placeholder": "Teslim edilen kişi",
            "required": True,
            "assignment_only": True,
            "options_key": "responsibles",
        },
    ],
    "yazici": [
        {
            "key": "inventory_no",
            "label": "Envanter No",
            "placeholder": "IPY-001",
            "required": True,
        },
        {
            "key": "brand",
            "label": "Marka",
            "placeholder": "Marka",
            "required": True,
        },
        {
            "key": "model",
            "label": "Model",
            "placeholder": "Model",
            "required": True,
        },
        {
            "key": "serial_no",
            "label": "Seri No",
            "placeholder": "Seri numarası",
            "required": False,
        },
        {
            "key": "usage_area",
            "label": "Kullanım Alanı",
            "placeholder": "Örn. Finans",
            "required": False,
            "assignment_only": True,
            "options_key": "usage_areas",
        },
        {
            "key": "factory",
            "label": "Fabrika",
            "placeholder": "Fabrika adı",
            "required": True,
            "assignment_only": True,
            "options_key": "factories",
        },
        {
            "key": "hostname",
            "label": "Hostname",
            "placeholder": "PRN-OFIS-01",
            "required": False,
            "assignment_only": True,
        },
        {
            "key": "ip_address",
            "label": "IP Adresi",
            "placeholder": "10.0.0.10",
            "required": False,
            "assignment_only": True,
        },
        {
            "key": "mac_address",
            "label": "MAC Adresi",
            "placeholder": "AA:BB:CC:DD:EE:FF",
            "required": False,
            "assignment_only": True,
        },
        {
            "key": "responsible",
            "label": "Sorumlu",
            "placeholder": "Sorumlu kişi",
            "required": True,
            "assignment_only": True,
            "options_key": "responsibles",
        },
    ],
    "lisans": [
        {
            "key": "license_name",
            "label": "Lisans Adı",
            "placeholder": "Ürün adı",
            "required": True,
            "options_key": "license_names",
        },
        {
            "key": "license_key",
            "label": "Lisans Anahtarı",
            "placeholder": "XXXX-XXXX-XXXX",
            "required": True,
        },
        {
            "key": "inventory_no",
            "label": "Bağlı Envanter",
            "placeholder": "ENV-001",
            "required": False,
            "options_key": "inventory_numbers",
        },
        {
            "key": "factory",
            "label": "Fabrika",
            "placeholder": "Fabrika adı",
            "required": False,
            "assignment_only": True,
            "options_key": "factories",
        },
        {
            "key": "department",
            "label": "Departman",
            "placeholder": "Departman",
            "required": False,
            "assignment_only": True,
            "options_key": "departments",
        },
        {
            "key": "responsible",
            "label": "Sorumlu",
            "placeholder": "Teslim edilen kişi",
            "required": False,
            "assignment_only": True,
            "options_key": "responsibles",
        },
    ],
    "talep": [
        {
            "key": "hardware_type",
            "label": "Donanım Tipi",
            "placeholder": "Donanım tipi",
            "required": True,
        },
        {
            "key": "brand",
            "label": "Marka",
            "placeholder": "Marka",
            "required": False,
        },
        {
            "key": "model",
            "label": "Model",
            "placeholder": "Model",
            "required": False,
        },
        {
            "key": "department",
            "label": "Departman",
            "placeholder": "Departman",
            "required": False,
        },
    ],
    "manuel": [
        {
            "key": "hardware_type",
            "label": "Donanım Tipi",
            "placeholder": "Donanım tipi",
            "required": True,
        },
        {
            "key": "brand",
            "label": "Marka",
            "placeholder": "Marka",
            "required": False,
        },
        {
            "key": "model",
            "label": "Model",
            "placeholder": "Model",
            "required": False,
        },
    ],
}


THEME_OPTIONS = {
    "varsayilan": {
        "label": "Varsayılan",
        "description": "Hafif mavi tonlarda, modern varsayılan görünüm.",
        "preview": {"bg": "#eef4ff", "fg": "#1f2933"},
    },
    "gece": {
        "label": "Gece Modu",
        "description": "Koyu arka plan ve yüksek kontrastlı metinler.",
        "preview": {"bg": "#111827", "fg": "#f9fafb"},
    },
    "okyanus": {
        "label": "Okyanus",
        "description": "Serin mavi ve turkuaz geçişleriyle dinlendirici bir tema.",
        "preview": {"bg": "#0f172a", "fg": "#38bdf8"},
    },
    "orman": {
        "label": "Orman",
        "description": "Yeşil tonlarda doğal ve sakin bir görünüm.",
        "preview": {"bg": "#0b3d2e", "fg": "#c3f0ca"},
    },
    "gunes": {
        "label": "Güneş",
        "description": "Sıcak sarı ve turuncu vurgularla enerjik bir tema.",
        "preview": {"bg": "#fff7ed", "fg": "#c2410c"},
    },
    "lavanta": {
        "label": "Lavanta",
        "description": "Mor ve pembe pastel tonlarda yumuşak bir görünüm.",
        "preview": {"bg": "#f3e8ff", "fg": "#6d28d9"},
    },
}


def ensure_user_profile_columns() -> None:
    existing_columns = {
        row[1]
        for row in db.session.execute(text("PRAGMA table_info(users)")).fetchall()
    }
    altered = False

    if "preferred_theme" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE users ADD COLUMN preferred_theme VARCHAR(64)"
                " DEFAULT 'varsayilan'"
            )
        )
        altered = True

    if "password_hash" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
        )
        altered = True

    if "system_role" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE users ADD COLUMN system_role VARCHAR(32)"
                " DEFAULT 'user'"
            )
        )
        altered = True

    if "must_change_password" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN"
                " NOT NULL DEFAULT 0"
            )
        )
        altered = True

    if altered:
        db.session.commit()


def ensure_request_line_category_column() -> None:
    existing_columns = {
        row[1]
        for row in db.session.execute(text("PRAGMA table_info(request_lines)")).fetchall()
    }
    if "category" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE request_lines ADD COLUMN category VARCHAR(32)"
                " NOT NULL DEFAULT 'envanter'"
            )
        )
        db.session.execute(
            text(
                "UPDATE request_lines SET category = 'envanter'"
                " WHERE category IS NULL OR TRIM(category) = ''"
            )
        )
        db.session.commit()


def get_active_user() -> User | None:
    user_id = session.get("active_user_id")
    if user_id is None:
        return None

    user: User | None = User.query.get(user_id)
    if user is None:
        session.pop("active_user_id", None)
    return user


def set_active_user(user: User | None) -> None:
    if user is None:
        session.pop("active_user_id", None)
    else:
        session["active_user_id"] = user.id


def get_system_role(user: User | None) -> str:
    if user is None:
        return "user"
    role = (user.system_role or "user").strip().lower()
    return role if role in SYSTEM_ROLE_LEVELS else "user"


def has_system_role(user: User | None, required: str) -> bool:
    required_role = (required or "user").strip().lower()
    if required_role not in SYSTEM_ROLE_LEVELS:
        required_role = "user"
    user_role = get_system_role(user)
    return SYSTEM_ROLE_LEVELS[user_role] >= SYSTEM_ROLE_LEVELS[required_role]


def current_actor_name() -> str:
    user = get_active_user()
    if not user:
        return DEFAULT_EVENT_ACTOR
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username or DEFAULT_EVENT_ACTOR


def is_safe_redirect_target(target: str | None) -> bool:
    if not target:
        return False
    target = target.strip()
    if not target:
        return False
    if target.startswith("//"):
        return False
    parsed_target = urlparse(target)
    if parsed_target.scheme and parsed_target.scheme not in {"http", "https"}:
        return False
    if parsed_target.netloc and parsed_target.netloc != urlparse(request.host_url).netloc:
        return False
    return True


def split_license_name(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    if " - " in value:
        name, key = value.split(" - ", 1)
        return name.strip(), key.strip()
    return value.strip(), ""


def create_app() -> Flask:
    data_dir = Path("/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    database_path = data_dir / "stok.db"
    info_upload_dir = data_dir / "info_uploads"
    info_upload_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="stok-admin-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    app.config["INFO_UPLOAD_DIR"] = info_upload_dir
    app.config["DATABASE_PATH"] = database_path
    app.permanent_session_lifetime = timedelta(hours=8)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_user_profile_columns()
        ensure_request_line_category_column()
        seed_initial_data()

    @app.before_request
    def enforce_login():
        endpoint = request.endpoint or ""
        if endpoint in {"login", "static", "force_password_change"}:
            return
        if endpoint.startswith("static"):
            return

        user = get_active_user()
        if user is not None:
            if user.must_change_password:
                allowed = {"force_password_change", "logout"}
                if endpoint not in allowed:
                    if request.path.startswith("/api/"):
                        return (
                            jsonify(
                                {
                                    "error": "Devam etmek için lütfen ilk giriş şifrenizi güncelleyin.",
                                }
                            ),
                            403,
                        )
                    if request.method == "GET":
                        next_url = request.full_path or request.path
                        if next_url.endswith("?"):
                            next_url = next_url[:-1]
                        if is_safe_redirect_target(next_url):
                            session["post_password_change_redirect"] = next_url
                    return redirect(url_for("force_password_change"))
            return

        if request.path.startswith("/api/"):
            return jsonify({"error": "Bu işlemi yapmak için oturum açın."}), 401

        next_url = ""
        if request.method == "GET":
            next_url = request.full_path or request.path
            if next_url.endswith("?"):
                next_url = next_url[:-1]
        target = next_url if is_safe_redirect_target(next_url) else None
        return redirect(url_for("login", next=target))

    @app.context_processor
    def inject_profile_preferences() -> dict[str, Any]:
        user = get_active_user()
        theme_key = "varsayilan"
        if user and user.preferred_theme in THEME_OPTIONS:
            theme_key = user.preferred_theme
        theme_meta = THEME_OPTIONS.get(theme_key, THEME_OPTIONS["varsayilan"])
        return {
            "active_user": user,
            "active_system_role": get_system_role(user),
            "active_theme": theme_key,
            "active_theme_meta": theme_meta,
            "active_theme_class": f"theme-{theme_key}",
            "theme_options": THEME_OPTIONS,
            "system_role_labels": SYSTEM_ROLE_LABELS,
            "is_admin_user": has_system_role(user, "admin"),
            "is_super_admin": has_system_role(user, "superadmin"),
        }

    @app.route("/giris", methods=["GET", "POST"])
    def login():
        if get_active_user():
            next_param = request.args.get("next")
            if next_param and is_safe_redirect_target(next_param):
                return redirect(next_param)
            return redirect(url_for("index"))

        error: str | None = None
        next_param = request.args.get("next")

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            next_param = request.form.get("next") or next_param

            user = (
                User.query.filter(func.lower(User.username) == username.lower()).first()
                if username
                else None
            )

            if user and user.password_hash and check_password_hash(user.password_hash, password):
                session.clear()
                session.permanent = True
                set_active_user(user)
                record_activity(
                    area="auth",
                    action="Oturum açıldı",
                    actor=current_actor_name(),
                    metadata={"user_id": user.id, "username": user.username},
                )
                db.session.commit()
                target = next_param if is_safe_redirect_target(next_param) else None
                if user.must_change_password:
                    session.pop("post_password_change_redirect", None)
                    if target:
                        session["post_password_change_redirect"] = target
                    return redirect(url_for("force_password_change"))
                session.pop("post_password_change_redirect", None)
                return redirect(target or url_for("index"))

            error = "Kullanıcı adı veya şifre hatalı."

        return render_template(
            "login.html",
            error=error,
            next_target=next_param if is_safe_redirect_target(next_param) else "",
        )

    @app.route("/ilk-giris-sifre", methods=["GET", "POST"])
    def force_password_change():
        user = get_active_user()
        if user is None:
            flash("Lütfen önce oturum açın.", "warning")
            return redirect(url_for("login"))

        if not user.must_change_password:
            target = session.pop("post_password_change_redirect", None)
            if target and is_safe_redirect_target(target):
                return redirect(target)
            target = None
        else:
            query_target = request.args.get("next")
            if query_target and is_safe_redirect_target(query_target):
                session["post_password_change_redirect"] = query_target
                target = query_target
            else:
                target = session.get("post_password_change_redirect")

        error: str | None = None

        if request.method == "POST":
            new_password = (request.form.get("new_password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()
            form_target = request.form.get("next")
            if form_target and is_safe_redirect_target(form_target):
                session["post_password_change_redirect"] = form_target
                target = form_target

            if not new_password or not confirm_password:
                error = "Lütfen yeni şifrenizi iki alana da yazın."
            elif new_password != confirm_password:
                error = "Yeni şifre ve doğrulama alanı eşleşmiyor."
            elif len(new_password) < 8:
                error = "Şifre en az 8 karakter olmalıdır."
            elif new_password.lower() == user.username.lower():
                error = "Şifreniz kullanıcı adınızla aynı olamaz."
            else:
                user.password_hash = generate_password_hash(new_password)
                user.must_change_password = False
                record_activity(
                    area="auth",
                    action="İlk giriş şifresi güncellendi",
                    actor=current_actor_name(),
                    metadata={"user_id": user.id, "username": user.username},
                )
                db.session.commit()
                flash("Yeni şifreniz kaydedildi.", "success")
                session.pop("post_password_change_redirect", None)
                if target and is_safe_redirect_target(target):
                    return redirect(target)
                return redirect(url_for("index"))

        return render_template(
            "force_password_change.html",
            error=error,
            next_target=target if target and is_safe_redirect_target(target) else "",
        )

    @app.route("/cikis")
    def logout():
        user = get_active_user()
        session.clear()
        if user:
            record_activity(
                area="auth",
                action="Oturum kapatıldı",
                actor=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={"user_id": user.id, "username": user.username},
            )
            db.session.commit()
        flash("Oturum kapatıldı.", "info")
        return redirect(url_for("login"))

    @app.route("/")
    def index():
        recent_activity = load_recent_activity()
        return render_template(
            "index.html",
            active_page="index",
            recent_activity=recent_activity,
        )

    @app.route("/envanter-takip")
    def inventory_tracking():
        payload = load_inventory_payload()
        return render_template(
            "inventory_tracking.html",
            active_page="inventory_tracking",
            **payload,
        )

    @app.route("/lisans-takip")
    def license_tracking():
        payload = load_license_payload()
        return render_template(
            "license_tracking.html",
            active_page="license_tracking",
            **payload,
        )

    @app.route("/yazici-takip")
    def printer_tracking():
        payload = load_printer_payload()
        return render_template(
            "printer_tracking.html",
            active_page="printer_tracking",
            **payload,
        )

    @app.route("/stok-takip")
    def stock_tracking():
        payload = load_stock_payload()
        return render_template(
            "stock_tracking.html",
            active_page="stock_tracking",
            **payload,
        )

    @app.route("/hurdalar")
    def scrap_inventory_page():
        payload = load_scrap_inventory_payload()
        can_restore = has_system_role(get_active_user(), "superadmin")
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            can_restore_scrap=can_restore,
            **payload,
        )

    @app.route("/profil")
    def profile():
        profile_user = get_active_user()
        can_switch_users = has_system_role(profile_user, "superadmin")
        users = (
            User.query.order_by(User.first_name, User.last_name).all()
            if can_switch_users
            else [profile_user] if profile_user else []
        )
        return render_template(
            "profile.html",
            active_page="profile",
            users=users,
            profile_user=profile_user,
            can_switch_users=can_switch_users,
        )

    @app.post("/profil/kullanici")
    def profile_switch_user():
        active_user = get_active_user()
        if not has_system_role(active_user, "superadmin"):
            flash("Bu işlemi gerçekleştirmek için yetkiniz yok.", "danger")
            return redirect(url_for("profile"))

        user_id = parse_int_or_none(request.form.get("user_id"))
        user = User.query.get(user_id) if user_id is not None else None

        if user is None:
            flash("Lütfen geçerli bir kullanıcı seçin.", "danger")
            return redirect(url_for("profile"))

        set_active_user(user)
        flash(f"{user.first_name} {user.last_name} profili görüntüleniyor.", "success")
        return redirect(url_for("profile"))

    @app.post("/profil/tema")
    def profile_update_theme():
        user = get_active_user()
        if user is None:
            flash("Tema güncellemek için kayıtlı kullanıcı bulunamadı.", "danger")
            return redirect(url_for("profile"))

        theme = (request.form.get("theme") or "").strip()
        if theme not in THEME_OPTIONS:
            flash("Lütfen geçerli bir tema seçin.", "warning")
            return redirect(url_for("profile"))

        user.preferred_theme = theme

        record_activity(
            area="profil",
            action="Tema güncellendi",
            description=f"{user.first_name} {user.last_name}",
            actor=current_actor_name(),
            metadata={"user_id": user.id, "theme": theme},
        )
        db.session.commit()
        flash("Tema tercihi güncellendi.", "success")
        return redirect(url_for("profile"))

    @app.post("/profil/sifre")
    def profile_update_password():
        user = get_active_user()
        if user is None:
            flash("Şifre güncellemek için kullanıcı bulunamadı.", "danger")
            return redirect(url_for("profile"))

        new_password = (request.form.get("new_password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        if not new_password or not confirm_password:
            flash("Lütfen yeni şifre alanlarını doldurun.", "warning")
            return redirect(url_for("profile"))

        if new_password != confirm_password:
            flash("Yeni şifre ve doğrulama şifresi eşleşmiyor.", "danger")
            return redirect(url_for("profile"))

        if len(new_password) < 8:
            flash("Şifre en az 8 karakter olmalıdır.", "warning")
            return redirect(url_for("profile"))

        user.password_hash = generate_password_hash(new_password)
        user.must_change_password = False

        record_activity(
            area="profil",
            action="Şifre güncellendi",
            description=f"{user.first_name} {user.last_name}",
            actor=current_actor_name(),
            metadata={"user_id": user.id},
        )
        db.session.commit()
        flash("Şifre başarıyla güncellendi.", "success")
        return redirect(url_for("profile"))

    @app.route("/uploads/info/<path:filename>")
    def info_uploads(filename: str):
        upload_dir: Path = app.config["INFO_UPLOAD_DIR"]
        return send_from_directory(upload_dir, filename)

    @app.route("/bilgiler")
    def information_list():
        payload = load_information_payload()
        return render_template(
            "information/list.html",
            active_page="information",
            **payload,
        )

    @app.post("/bilgiler")
    def create_information_entry():
        title = (request.form.get("title") or "").strip()
        category_id = parse_int_or_none(request.form.get("category_id"))
        content = (request.form.get("content") or "").strip()

        if not title or not category_id or not content:
            flash("Lütfen başlık, kategori ve içerik alanlarını doldurun.", "danger")
            return redirect(url_for("information_list"))

        category = InfoCategory.query.get(category_id)
        if category is None:
            flash("Seçilen kategori bulunamadı.", "danger")
            return redirect(url_for("information_list"))

        image_filename = save_information_image(request.files.get("photo"))

        entry = InfoEntry(
            title=title,
            category=category,
            content=content,
            image_filename=image_filename,
        )
        attachments = request.files.getlist("attachments")
        for file in attachments:
            saved = save_information_file(file)
            if not saved:
                continue
            stored_name, original_name = saved
            entry.attachments.append(
                InfoAttachment(
                    filename=stored_name,
                    original_name=original_name,
                    content_type=file.mimetype,
                )
            )
        db.session.add(entry)
        db.session.flush()

        record_activity(
            area="bilgi",
            action="Bilgi kaydı oluşturuldu",
            description=title,
            metadata={"info_id": entry.id},
        )

        db.session.commit()

        flash("Bilgi kaydı başarıyla oluşturuldu.", "success")
        return redirect(url_for("information_list"))

    @app.route("/bilgiler/<int:entry_id>")
    def information_detail(entry_id: int):
        entry = load_information_entry(entry_id)
        if entry is None:
            abort(404)

        categories = InfoCategory.query.order_by(InfoCategory.name).all()
        return render_template(
            "information/detail.html",
            active_page="information",
            entry=entry,
            categories=categories,
            mode="view",
        )

    @app.route("/bilgiler/<int:entry_id>/duzenle", methods=["GET", "POST"])
    def information_edit(entry_id: int):
        entry = load_information_entry(entry_id)
        if entry is None:
            abort(404)

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            category_id = parse_int_or_none(request.form.get("category_id"))
            content = (request.form.get("content") or "").strip()

            if not title or not category_id or not content:
                flash("Lütfen başlık, kategori ve içerik alanlarını doldurun.", "danger")
                return redirect(url_for("information_edit", entry_id=entry.id))

            category = InfoCategory.query.get(category_id)
            if category is None:
                flash("Seçilen kategori bulunamadı.", "danger")
                return redirect(url_for("information_edit", entry_id=entry.id))

            entry.title = title
            entry.category = category
            entry.content = content

            new_filename = save_information_image(request.files.get("photo"))
            if new_filename:
                remove_information_image(entry.image_filename)
                entry.image_filename = new_filename

            remove_ids = {
                parse_int_or_none(raw)
                for raw in request.form.getlist("remove_attachments")
            }
            remove_ids.discard(None)
            if remove_ids:
                for attachment in list(entry.attachments):
                    if attachment.id in remove_ids:
                        remove_information_file(attachment.filename)
                        db.session.delete(attachment)

            new_attachments = request.files.getlist("attachments")
            for file in new_attachments:
                saved = save_information_file(file)
                if not saved:
                    continue
                stored_name, original_name = saved
                entry.attachments.append(
                    InfoAttachment(
                        filename=stored_name,
                        original_name=original_name,
                        content_type=file.mimetype,
                    )
                )

            record_activity(
                area="bilgi",
                action="Bilgi kaydı güncellendi",
                description=title,
                metadata={"info_id": entry.id},
            )

            db.session.commit()

            flash("Bilgi kaydı güncellendi.", "success")
            return redirect(url_for("information_detail", entry_id=entry.id))

        categories = InfoCategory.query.order_by(InfoCategory.name).all()
        return render_template(
            "information/detail.html",
            active_page="information",
            entry=entry,
            categories=categories,
            mode="edit",
        )

    @app.route("/admin-panel")
    def admin_panel():
        user = get_active_user()
        if not has_system_role(user, "admin"):
            flash("Admin paneline erişmek için yetkiniz yok.", "danger")
            return redirect(url_for("index"))
        admin_payload = load_admin_panel_payload()
        return render_template(
            "admin_panel.html",
            active_page="admin_panel",
            can_manage_users=has_system_role(user, "superadmin"),
            can_manage_data=has_system_role(user, "superadmin"),
            system_role_choices=[
                {"value": key, "label": SYSTEM_ROLE_LABELS[key]}
                for key in ("user", "admin")
            ],
            **admin_payload,
        )

    @app.get("/admin-panel/data/export")
    def export_database():
        user = get_active_user()
        if not has_system_role(user, "superadmin"):
            flash("Veri dışa aktarma işlemi için süper admin yetkisi gerekir.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        database_path = get_database_path()
        if not database_path.exists():
            flash("Veritabanı dosyası bulunamadı.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        record_activity(
            area="sistem",
            action="Veritabanı yedeği indirildi",
            description="Sistem yöneticisi mevcut veritabanını indirdi.",
            actor=current_actor_name(),
        )
        db.session.commit()

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return send_file(
            database_path,
            as_attachment=True,
            download_name=f"stok-veritabani-{timestamp}.db",
            mimetype="application/x-sqlite3",
        )

    @app.post("/admin-panel/data/import")
    def import_database_backup():
        user = get_active_user()
        if not has_system_role(user, "superadmin"):
            flash("Veri içe aktarma işlemi için süper admin yetkisi gerekir.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        file: FileStorage | None = request.files.get("data_file")
        if file is None or not file.filename:
            flash("Lütfen bir veritabanı yedeği seçin.", "warning")
            return redirect(url_for("admin_panel", section="data-section"))

        filename = secure_filename(file.filename)
        extension = Path(filename).suffix.lower()
        if extension not in {".db", ".sqlite", ".sqlite3"}:
            flash("Yalnızca SQLite veritabanı dosyaları içe aktarılabilir.", "warning")
            return redirect(url_for("admin_panel", section="data-section"))

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                file.save(tmp.name)
                temp_path = Path(tmp.name)
        except Exception:
            flash("Yüklenen dosya kaydedilirken bir hata oluştu.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        try:
            connection = sqlite3.connect(temp_path)
            connection.execute("PRAGMA schema_version;")
            connection.close()
        except sqlite3.Error:
            temp_path.unlink(missing_ok=True)
            flash("Yüklenen dosya geçerli bir SQLite veritabanı değil.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        database_path = get_database_path()
        backup_path = database_path.with_suffix(".bak")

        try:
            if database_path.exists():
                shutil.copy2(database_path, backup_path)

            db.session.remove()
            db.engine.dispose()

            shutil.copy2(temp_path, database_path)

            db.create_all()
            ensure_user_profile_columns()
            ensure_request_line_category_column()
        except Exception:  # pragma: no cover - güvenlik amaçlı kayıt
            current_app.logger.exception("Veritabanı içe aktarılamadı")
            if backup_path.exists():
                shutil.copy2(backup_path, database_path)
            flash("Veritabanı içe aktarılırken bir hata oluştu.", "danger")
            temp_path.unlink(missing_ok=True)
            return redirect(url_for("admin_panel", section="data-section"))
        finally:
            temp_path.unlink(missing_ok=True)

        record_activity(
            area="sistem",
            action="Veritabanı yedeği içe aktarıldı",
            description="Sistem verileri yeni bir yedekten geri yüklendi.",
            actor=current_actor_name(),
        )
        db.session.commit()

        flash("Veritabanı yedeği başarıyla içe aktarıldı.", "success")
        return redirect(url_for("admin_panel", section="data-section"))

    @app.post("/admin-panel/data/reset")
    def reset_database_view():
        user = get_active_user()
        if not has_system_role(user, "superadmin"):
            flash("Veritabanını sıfırlamak için süper admin yetkisi gerekir.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        info_upload_dir = Path(current_app.config.get("INFO_UPLOAD_DIR", Path("/data/info_uploads")))

        try:
            db.session.remove()
            db.drop_all()
            db.create_all()
            ensure_user_profile_columns()
            ensure_request_line_category_column()
            if info_upload_dir.exists():
                shutil.rmtree(info_upload_dir, ignore_errors=True)
            info_upload_dir.mkdir(parents=True, exist_ok=True)
            seed_initial_data()
            record_activity(
                area="sistem",
                action="Veritabanı sıfırlandı",
                description="Sistem varsayılan başlangıç verileriyle yeniden oluşturuldu.",
                actor=current_actor_name(),
            )
            db.session.commit()
        except Exception:  # pragma: no cover - güvenlik amaçlı kayıt
            current_app.logger.exception("Veritabanı sıfırlanamadı")
            flash("Veritabanı sıfırlanırken bir hata oluştu.", "danger")
            return redirect(url_for("admin_panel", section="data-section"))

        flash("Veritabanı varsayılan verilerle yeniden oluşturuldu.", "success")
        return redirect(url_for("admin_panel", section="data-section"))

    @app.post("/admin-panel/users")
    def create_user():
        active_user = get_active_user()
        if not has_system_role(active_user, "superadmin"):
            flash("Yeni kullanıcı oluşturmak için süper admin yetkisi gerekir.", "danger")
            return redirect(url_for("admin_panel"))

        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        system_role = (request.form.get("system_role") or "user").strip().lower() or "user"

        if system_role not in {"user", "admin"}:
            system_role = "user"

        if not all([username, first_name, last_name, email]):
            flash("Lütfen tüm alanları doldurun.", "danger")
            return redirect(url_for("admin_panel"))

        if len(password) < 8:
            flash("Şifre en az 8 karakter olmalıdır.", "warning")
            return redirect(url_for("admin_panel"))

        existing_username = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_username or existing_email:
            flash("Bu kullanıcı adı veya e-posta zaten kullanılıyor.", "warning")
            return redirect(url_for("admin_panel"))

        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role="",  # roller ileride admin panelinden düzenlenecek
            department="",
            password_hash=generate_password_hash(password),
            system_role=system_role,
            must_change_password=True,
        )
        db.session.add(user)
        db.session.flush()

        record_activity(
            area="kullanici",
            action="Kullanıcı oluşturuldu",
            description=f"{first_name} {last_name} ({username}) eklendi.",
            actor=current_actor_name(),
            metadata={
                "user_id": user.id,
                "email": email,
                "system_role": system_role,
            },
        )

        db.session.commit()

        flash("Yeni kullanıcı başarıyla oluşturuldu.", "success")
        return redirect(url_for("admin_panel"))

    @app.post("/admin-panel/users/<int:user_id>/delete")
    def delete_user(user_id: int):
        active_user = get_active_user()
        if not has_system_role(active_user, "superadmin"):
            flash("Kullanıcı silmek için süper admin yetkisi gerekir.", "danger")
            return redirect(url_for("admin_panel"))

        user = User.query.get(user_id)
        if user is None:
            flash("Silinmek istenen kullanıcı bulunamadı.", "danger")
            return redirect(url_for("admin_panel"))

        active_user = get_active_user()
        was_active_user = active_user is not None and active_user.id == user.id

        display_name = f"{user.first_name} {user.last_name}".strip()
        if display_name:
            description = f"{display_name} ({user.username}) kullanıcısı silindi."
        else:
            description = f"{user.username} kullanıcısı silindi."

        metadata = {"user_id": user.id, "email": user.email}

        if user.system_role == "superadmin":
            remaining_superadmins = (
                User.query.filter(func.lower(User.system_role) == "superadmin")
                .filter(User.id != user.id)
                .count()
            )
            if remaining_superadmins == 0:
                flash("Son süper admin kullanıcısı silinemez.", "warning")
                return redirect(url_for("admin_panel"))

        db.session.delete(user)
        record_activity(
            area="kullanici",
            action="Kullanıcı silindi",
            description=description,
            actor=current_actor_name(),
            metadata=metadata,
        )
        db.session.commit()

        if was_active_user:
            session.clear()

        flash("Kullanıcı başarıyla silindi.", "success")
        return redirect(url_for("admin_panel"))

    @app.post("/api/options/<string:option_key>")
    def create_option(option_key: str):
        if option_key == "brands":
            return create_brand()

        model = OPTION_MODEL_MAPPING.get(option_key)
        if not model:
            abort(404)

        try:
            name = parse_option_name(request.get_json())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if find_existing_by_name(model, name):
            return jsonify({"error": "Bu kayıt zaten mevcut."}), 409

        option = model(name=name)
        db.session.add(option)
        db.session.commit()

        return jsonify(option.to_dict()), 201

    @app.delete("/api/options/<string:option_key>/<int:option_id>")
    def delete_option(option_key: str, option_id: int):
        if option_key == "brands":
            return delete_brand(option_id)

        model = OPTION_MODEL_MAPPING.get(option_key)
        if not model:
            abort(404)

        option = model.query.get(option_id)
        if option is None:
            return jsonify({"error": "Kayıt bulunamadı."}), 404

        db.session.delete(option)
        db.session.commit()
        return ("", 204)

    @app.post("/api/options/brands/<int:brand_id>/models")
    def create_model(brand_id: int):
        brand = Brand.query.get(brand_id)
        if brand is None:
            return jsonify({"error": "Marka bulunamadı."}), 404

        try:
            name = parse_option_name(request.get_json())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        existing = (
            HardwareModel.query.filter_by(brand_id=brand.id)
            .filter(func.lower(HardwareModel.name) == name.lower())
            .first()
        )
        if existing:
            return jsonify({"error": "Bu model zaten mevcut."}), 409

        model = HardwareModel(name=name, brand=brand)
        db.session.add(model)
        db.session.commit()
        return jsonify(model.to_dict()), 201

    @app.delete("/api/options/models/<int:model_id>")
    def delete_model(model_id: int):
        model = HardwareModel.query.get(model_id)
        if model is None:
            return jsonify({"error": "Model bulunamadı."}), 404

        db.session.delete(model)
        db.session.commit()
        return ("", 204)

    @app.post("/api/inventory")
    def create_inventory():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        inventory_no = (data.get("inventory_no") or "").strip()
        if not inventory_no:
            return json_error("Envanter numarası zorunludur."), 400

        existing = InventoryItem.query.filter_by(inventory_no=inventory_no).first()
        if existing:
            return json_error("Bu envanter numarası zaten kullanılıyor."), 409

        factory_id = parse_int_or_none(data.get("factory_id"))
        hardware_type_id = parse_int_or_none(data.get("hardware_type_id"))
        brand_id = parse_int_or_none(data.get("brand_id"))
        model_id = parse_int_or_none(data.get("model_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))

        factory = Factory.query.get(factory_id) if factory_id else None
        hardware_type = HardwareType.query.get(hardware_type_id) if hardware_type_id else None
        brand = Brand.query.get(brand_id) if brand_id else None
        model = HardwareModel.query.get(model_id) if model_id else None
        responsible_user = User.query.get(responsible_user_id) if responsible_user_id else None

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if not hardware_type:
            return json_error("Geçerli bir donanım tipi seçin."), 400
        if not brand:
            return json_error("Geçerli bir marka seçin."), 400
        if not model:
            return json_error("Geçerli bir model seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400

        department = (data.get("department") or "").strip()
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        item = InventoryItem(
            inventory_no=inventory_no,
            computer_name=(data.get("computer_name") or "").strip() or None,
            factory_id=factory_id,
            department=department,
            hardware_type_id=hardware_type_id,
            responsible_user_id=responsible_user_id,
            brand_id=brand_id,
            model_id=model_id,
            serial_no=(data.get("serial_no") or "").strip() or None,
            ifs_no=(data.get("ifs_no") or "").strip() or None,
            related_machine_no=(data.get("related_machine_no") or "").strip() or None,
            note=(data.get("note") or "").strip() or None,
        )
        db.session.add(item)
        db.session.flush()
        add_inventory_event(item, "Envanter oluşturuldu")
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return (
            jsonify({"item": serialize_inventory_item(fresh_item)}),
            201,
        )

    @app.patch("/api/inventory/<int:item_id>")
    def update_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        inventory_no = (data.get("inventory_no") or item.inventory_no or "").strip()
        if not inventory_no:
            return json_error("Envanter numarası zorunludur."), 400

        if (
            inventory_no != item.inventory_no
            and InventoryItem.query.filter_by(inventory_no=inventory_no).first()
        ):
            return json_error("Bu envanter numarası zaten kullanılıyor."), 409

        factory_id = parse_int_or_none(data.get("factory_id"))
        hardware_type_id = parse_int_or_none(data.get("hardware_type_id"))
        brand_id = parse_int_or_none(data.get("brand_id"))
        model_id = parse_int_or_none(data.get("model_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))

        factory = Factory.query.get(factory_id) if factory_id else None
        hardware_type = HardwareType.query.get(hardware_type_id) if hardware_type_id else None
        brand = Brand.query.get(brand_id) if brand_id else None
        model = HardwareModel.query.get(model_id) if model_id else None
        responsible_user = User.query.get(responsible_user_id) if responsible_user_id else None

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if not hardware_type:
            return json_error("Geçerli bir donanım tipi seçin."), 400
        if not brand:
            return json_error("Geçerli bir marka seçin."), 400
        if not model:
            return json_error("Geçerli bir model seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400

        department = (data.get("department") or "").strip()
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        status = (data.get("status") or item.status or "aktif").strip().lower()
        if status not in INVENTORY_STATUSES:
            return json_error("Geçersiz durum değeri."), 400

        item.inventory_no = inventory_no
        item.computer_name = (data.get("computer_name") or "").strip() or None
        item.factory = factory
        item.department = department
        item.hardware_type = hardware_type
        item.responsible_user = responsible_user
        item.brand = brand
        item.model = model
        item.serial_no = (data.get("serial_no") or "").strip() or None
        item.ifs_no = (data.get("ifs_no") or "").strip() or None
        if "related_machine_no" in data:
            item.related_machine_no = (data.get("related_machine_no") or "").strip() or None
        if "machine_no" in data:
            item.machine_no = (data.get("machine_no") or "").strip() or None
        item.note = (data.get("note") or "").strip() or None
        item.status = status

        add_inventory_event(item, "Envanter bilgileri güncellendi")
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @app.post("/api/inventory/<int:item_id>/assign")
    def assign_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        factory_id = parse_int_or_none(data.get("factory_id"))
        responsible_user_id = parse_int_or_none(data.get("responsible_user_id"))
        department = (data.get("department") or "").strip()

        factory = Factory.query.get(factory_id) if factory_id else None
        responsible_user = User.query.get(responsible_user_id) if responsible_user_id else None

        if not factory:
            return json_error("Geçerli bir fabrika seçin."), 400
        if responsible_user_id and not responsible_user:
            return json_error("Geçerli bir kullanıcı seçin."), 400
        if not department:
            return json_error("Departman alanı zorunludur."), 400

        item.factory = factory
        item.department = department
        item.responsible_user = responsible_user
        if "related_machine_no" in data:
            item.related_machine_no = (data.get("related_machine_no") or "").strip() or None

        note_parts: list[str] = []
        note_parts.append(f"Fabrika: {factory.name}")
        note_parts.append(f"Departman: {department}")
        if responsible_user:
            note_parts.append(
                f"Sorumlu: {responsible_user.first_name} {responsible_user.last_name}"
            )

        add_inventory_event(item, "Atama güncellendi", " • ".join(note_parts))
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @app.post("/api/inventory/<int:item_id>/mark-faulty")
    def mark_inventory_faulty(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        reason = (data.get("reason") or "").strip()
        location = (data.get("location") or "").strip()
        note_parts = []
        if reason:
            note_parts.append(f"Arıza Nedeni: {reason}")
        if location:
            note_parts.append(f"Gönderildiği Yer: {location}")

        item.status = "arizali"
        add_inventory_event(item, "Arıza bildirimi", " • ".join(note_parts))
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @app.post("/api/inventory/<int:item_id>/stock")
    def move_inventory_to_stock(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        existing_stock = (
            StockItem.query.options(
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.hardware_type),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.factory),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.brand),
                joinedload(StockItem.inventory_item).joinedload(InventoryItem.model),
                joinedload(StockItem.logs),
            )
            .filter(StockItem.inventory_item_id == item.id)
            .order_by(StockItem.id.desc())
            .first()
        )

        if existing_stock and existing_stock.status == "stokta":
            return json_error("Bu envanter kaydı zaten stokta."), 409

        item.status = "stokta"
        add_inventory_event(item, "Stok girişi", note, performed_by=actor)

        log_entry = None
        if existing_stock:
            metadata_payload = build_inventory_stock_metadata(item)
            existing_stock.status = "stokta"
            existing_stock.quantity = 1
            existing_stock.reference_code = item.inventory_no
            existing_stock.source_type = "inventory"
            existing_stock.inventory_item = item
            if note:
                existing_stock.note = note
            existing_stock.metadata_payload = {
                key: value for key, value in metadata_payload.items() if value
            }
            log_entry = record_stock_log(
                existing_stock,
                "Envanter stoğa geri alındı",
                action_type="in",
                performed_by=actor,
                quantity_change=0,
                note=note,
                metadata={"inventory_no": item.inventory_no},
            )
            stock_item = existing_stock
        else:
            stock_item = create_stock_item_from_inventory(item, note=note, actor=actor)

        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        payload: dict[str, Any] = {"item": serialize_inventory_item(fresh_item)}
        if stock_item:
            fresh_stock = get_stock_item_with_relations(stock_item.id)
            if fresh_stock:
                payload["stock_item"] = serialize_stock_item(fresh_stock)
                if log_entry:
                    payload["log"] = serialize_stock_log(log_entry)
                elif fresh_stock.logs:
                    payload["log"] = serialize_stock_log(fresh_stock.logs[0])
        return jsonify(payload)

    @app.post("/api/inventory/<int:item_id>/scrap")
    def scrap_inventory(item_id: int):
        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        item.status = "hurda"
        if note:
            item.note = note
        add_inventory_event(item, "Hurdaya ayırma", note)
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @app.post("/api/licenses/<int:license_id>/stock")
    def move_license_to_stock(license_id: int):
        license = (
            InventoryLicense.query.options(
                joinedload(InventoryLicense.item)
                .joinedload(InventoryItem.factory)
                .joinedload(InventoryItem.hardware_type),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.brand),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.model),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.responsible_user),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
            )
            .filter_by(id=license_id)
            .first()
        )
        if license is None:
            return json_error("Lisans kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        associated_item = license.item
        stock_item = create_stock_item_from_license(license, note=note, actor=actor)

        license.status = "pasif"
        license.item = None

        if associated_item:
            add_inventory_event(
                associated_item,
                "Lisans stoklandı",
                note or f"{license.name} lisansı stok listesine taşındı.",
                performed_by=actor,
            )

        db.session.commit()

        fresh_license = (
            InventoryLicense.query.options(
                joinedload(InventoryLicense.item)
                .joinedload(InventoryItem.responsible_user),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.hardware_type),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.factory),
                joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
            )
            .filter_by(id=license.id)
            .first()
        )
        response: dict[str, Any] = {
            "message": "Lisans stok listesine taşındı.",
            "license": serialize_license_record(fresh_license) if fresh_license else None,
        }
        fresh_stock = get_stock_item_with_relations(stock_item.id)
        if fresh_stock:
            response["stock_item"] = serialize_stock_item(fresh_stock)
            if fresh_stock.logs:
                response["log"] = serialize_stock_log(fresh_stock.logs[0])
        return jsonify(response)

    @app.post("/api/stock")
    def create_stock_entry():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        title = (data.get("title") or "").strip()
        if not title:
            return json_error("Stok adı zorunludur."), 400

        category = normalize_stock_category(data.get("category"))
        quantity = parse_int_or_none(data.get("quantity"))
        if quantity is None:
            quantity = 1
        if quantity < 1:
            return json_error("Miktar en az 1 olmalıdır."), 400
        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR
        reference_code = (data.get("reference_code") or "").strip() or None
        unit = (data.get("unit") or "").strip() or None

        try:
            metadata_payload = prepare_stock_metadata(
                category,
                data.get("metadata"),
                include_assignment_fields=False,
            )
        except ValueError as exc:
            return json_error(str(exc)), 400

        if not reference_code:
            reference_code = (
                metadata_payload.get("inventory_no")
                or metadata_payload.get("license_key")
                or None
            )

        stock_item = StockItem(
            source_type="manual",
            title=title,
            category=category,
            quantity=quantity,
            status="stokta",
            reference_code=reference_code,
            unit=unit,
            note=note or None,
        )
        stock_item.metadata_payload = {
            k: v for k, v in metadata_payload.items() if v
        }
        db.session.add(stock_item)
        db.session.flush()

        log_entry = record_stock_log(
            stock_item,
            "Manuel stok girişi",
            action_type="in",
            performed_by=actor,
            quantity_change=stock_item.quantity,
            note=note,
        )

        db.session.commit()

        fresh_item = get_stock_item_with_relations(stock_item.id)
        response_payload: dict[str, Any] = {"stock_item": serialize_stock_item(fresh_item)}
        if log_entry:
            response_payload["log"] = serialize_stock_log(log_entry)
        return jsonify(response_payload), 201

    @app.post("/api/stock/<int:item_id>/assign")
    def assign_stock_item(item_id: int):
        stock_item = get_stock_item_with_relations(item_id)
        if stock_item is None:
            return json_error("Stok kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        category_value = normalize_stock_category(stock_item.category)
        metadata_defaults: dict[str, Any] = {}
        if stock_item.metadata_payload:
            metadata_defaults.update(stock_item.metadata_payload)
        if stock_item.inventory_item:
            metadata_defaults.update(
                {
                    k: v
                    for k, v in build_inventory_stock_metadata(stock_item.inventory_item).items()
                    if v
                }
            )

        try:
            assignment_metadata = prepare_stock_metadata(
                category_value,
                data.get("metadata"),
                defaults=metadata_defaults,
            )
        except ValueError as exc:
            return json_error(str(exc)), 400

        def sanitize(values: dict[str, Any]) -> dict[str, str]:
            cleaned: dict[str, str] = {}
            for key, raw in values.items():
                if raw is None:
                    continue
                text = str(raw).strip()
                if text:
                    cleaned[key] = text
            return cleaned

        combined_metadata = sanitize(metadata_defaults)
        combined_metadata.update(sanitize(assignment_metadata))
        stock_item.metadata_payload = combined_metadata or None

        stock_item.status = "devredildi"
        if note:
            stock_item.note = note

        if stock_item.inventory_item:
            inventory = stock_item.inventory_item
            inventory.status = "aktif"
            add_inventory_event(
                inventory,
                "Stoktan atama yapıldı",
                note or f"{stock_item.title} stoğa alınan ürün atandı.",
                performed_by=actor,
            )

        log_entry = record_stock_log(
            stock_item,
            "Stoktan atama yapıldı",
            action_type="out",
            performed_by=actor,
            quantity_change=-max(1, stock_item.quantity),
            note=note,
            metadata=assignment_metadata or None,
        )

        responsible_name = (stock_item.metadata_payload or {}).get("responsible")
        if responsible_name:
            record_activity(
                area="kullanici",
                action="Stok ataması",
                description=f"{stock_item.title} → {responsible_name}",
                actor=actor,
                metadata={
                    "stock_item_id": stock_item.id,
                    "category": category_value,
                    "responsible": responsible_name,
                    "inventory_no": (stock_item.metadata_payload or {}).get("inventory_no"),
                },
            )

        db.session.commit()

        fresh_item = get_stock_item_with_relations(stock_item.id)
        response_payload: dict[str, Any] = {"stock_item": serialize_stock_item(fresh_item)}
        if log_entry:
            response_payload["log"] = serialize_stock_log(log_entry)
        return jsonify(response_payload)

    @app.post("/api/stock/<int:item_id>/mark-faulty")
    def mark_stock_item_faulty(item_id: int):
        stock_item = get_stock_item_with_relations(item_id)
        if stock_item is None:
            return json_error("Stok kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        stock_item.status = "arizali"
        if note:
            stock_item.note = note

        if stock_item.inventory_item:
            inventory = stock_item.inventory_item
            inventory.status = "arizali"
            add_inventory_event(
                inventory,
                "Stok ürünü arızalı",
                note or f"{stock_item.title} stok kaydı arızalı işaretlendi.",
                performed_by=actor,
            )

        log_entry = record_stock_log(
            stock_item,
            "Stok ürünü arızalı işaretlendi",
            action_type="warning",
            performed_by=actor,
            note=note,
        )

        db.session.commit()

        fresh_item = get_stock_item_with_relations(stock_item.id)
        response_payload: dict[str, Any] = {"stock_item": serialize_stock_item(fresh_item)}
        if log_entry:
            response_payload["log"] = serialize_stock_log(log_entry)
        return jsonify(response_payload)

    @app.post("/api/stock/<int:item_id>/scrap")
    def scrap_stock_item(item_id: int):
        stock_item = get_stock_item_with_relations(item_id)
        if stock_item is None:
            return json_error("Stok kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        stock_item.status = "hurda"
        if note:
            stock_item.note = note

        if stock_item.inventory_item:
            inventory = stock_item.inventory_item
            inventory.status = "hurda"
            add_inventory_event(
                inventory,
                "Stok ürünü hurdaya ayrıldı",
                note or f"{stock_item.title} stok kaydı hurdaya ayrıldı.",
                performed_by=actor,
            )

        log_entry = record_stock_log(
            stock_item,
            "Stok ürünü hurdaya ayrıldı",
            action_type="out",
            performed_by=actor,
            quantity_change=-max(1, stock_item.quantity),
            note=note,
        )

        db.session.commit()

        fresh_item = get_stock_item_with_relations(stock_item.id)
        response_payload: dict[str, Any] = {"stock_item": serialize_stock_item(fresh_item)}
        if log_entry:
            response_payload["log"] = serialize_stock_log(log_entry)
        return jsonify(response_payload)

    @app.post("/api/inventory/<int:item_id>/restore-from-scrap")
    def restore_inventory_from_scrap(item_id: int):
        if not has_system_role(get_active_user(), "superadmin"):
            return jsonify(json_error("Bu işlemi yapmak için yetkiniz yok.")), 403

        item = get_inventory_item_with_relations(item_id)
        if item is None:
            return json_error("Envanter kaydı bulunamadı."), 404

        if (item.status or "").lower() != "hurda":
            return json_error("Bu kayıt hurda durumunda değil."), 400

        note = (request.get_json(silent=True) or {}).get("note")
        cleaned_note = (note or "").strip()

        item.status = "stokta"
        actor = current_actor_name()
        add_inventory_event(
            item,
            "Hurda kaydı geri alındı",
            cleaned_note or f"{item.inventory_no} kaydı stok durumuna döndürüldü.",
            performed_by=actor,
        )

        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        return jsonify({"item": serialize_inventory_item(fresh_item)})

    @app.post("/api/requests")
    def create_request():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        order_no = (data.get("order_no") or "").strip()
        requested_by = (data.get("requested_by") or "").strip()
        department = (data.get("department") or "").strip()
        active_user = get_active_user()
        requested_by_user = active_user
        group_key = (data.get("group_key") or "acik").strip().lower() or "acik"
        lines_payload = data.get("lines")

        if not order_no:
            return json_error("Sipariş numarası zorunludur."), 400
        if RequestOrder.query.filter_by(order_no=order_no).first():
            return json_error("Bu sipariş numarası zaten kayıtlı."), 409
        if not requested_by_user:
            return json_error("Talep sahibi doğrulanamadı."), 401

        requested_by = (
            f"{requested_by_user.first_name} {requested_by_user.last_name}".strip()
            or requested_by_user.username
        )
        department = (
            requested_by_user.department
            or department
            or "Belirtilmedi"
        )

        if not requested_by:
            return json_error("Talep sahibi seçin."), 400
        if not department:
            return json_error("Departman bilgisi zorunludur."), 400
        if not isinstance(lines_payload, list) or not lines_payload:
            return json_error("En az bir talep satırı ekleyin."), 400

        target_group = get_request_group_by_key(group_key) or get_request_group_by_key("acik")
        if target_group is None:
            return json_error("Talep grubu bulunamadı."), 400

        order = RequestOrder(
            order_no=order_no,
            requested_by=requested_by,
            department=department,
            group=target_group,
        )
        db.session.add(order)

        for index, raw_line in enumerate(lines_payload, start=1):
            if not isinstance(raw_line, dict):
                return json_error("Talep satırı formatı geçersiz."), 400
            hardware_type = (raw_line.get("hardware_type") or "").strip()
            brand = (raw_line.get("brand") or "").strip()
            model = (raw_line.get("model") or "").strip()
            quantity = parse_int_or_none(raw_line.get("quantity")) or 0
            note = (raw_line.get("note") or "").strip() or None
            category_value = normalize_stock_category(
                raw_line.get("category"),
                fallback="envanter",
            )

            if not hardware_type:
                return json_error(f"{index}. satır için donanım tipi zorunludur."), 400
            if quantity <= 0:
                return json_error(f"{index}. satır için geçerli bir miktar girin."), 400

            order.lines.append(
                RequestLine(
                    hardware_type=hardware_type,
                    brand=brand,
                    model=model,
                    quantity=quantity,
                    note=note,
                    category=category_value,
                )
            )

        db.session.flush()

        record_activity(
            area="talep",
            action="Yeni talep oluşturuldu",
            description=f"{order_no} numaralı talep {len(order.lines)} satır ile kaydedildi.",
            metadata={
                "order_id": order.id,
                "order_no": order.order_no,
                "department": order.department,
                "requested_by": requested_by,
                "requested_by_id": requested_by_user.id,
                "line_count": len(order.lines),
            },
        )

        db.session.commit()

        fresh_order = get_request_order_with_relations(order.id)
        payload = serialize_request_order(fresh_order)
        return (
            jsonify(
                {
                    "order": payload,
                    "message": f"{payload['order_no']} numaralı talep kaydedildi.",
                }
            ),
            201,
        )

    @app.post("/api/requests/<int:order_id>/actions")
    def update_request_status(order_id: int):
        order = get_request_order_with_relations(order_id)
        if order is None:
            return json_error("Talep kaydı bulunamadı."), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        action_key = (data.get("action") or "").strip().lower()
        quantity = parse_int_or_none(data.get("quantity"))
        if quantity is None:
            quantity = 1
        note = (data.get("note") or "").strip() or None
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        target_line_id = parse_int_or_none(data.get("line_id"))
        if target_line_id:
            target_lines = [line for line in order.lines if line.id == target_line_id]
            if not target_lines:
                return json_error("Talep satırı bulunamadı."), 404
        else:
            target_lines = list(order.lines)

        if action_key not in {"stok", "cancel"}:
            return json_error("Geçersiz işlem tipi."), 400

        total_quantity = sum(line.quantity for line in target_lines)
        if requested_quantity < 1:
            return json_error("Miktar en az 1 olmalıdır."), 400
        if total_quantity <= 0:
            return json_error("Talep satırları için geçerli miktar bulunamadı."), 400
        if requested_quantity > total_quantity:
            return json_error("Maksimum işlem miktarı aşılamaz."), 400

        processed_quantity = 0
        category_value = None
        validated_metadata: dict[str, str] | None = None
        if action_key == "stok":
            first_line = target_lines[0] if target_lines else None
            category_value = normalize_stock_category(
                first_line.category if first_line else None,
                fallback="envanter",
            )
            metadata_defaults = {}
            if first_line:
                metadata_defaults.update(
                    {
                        "hardware_type": first_line.hardware_type,
                        "brand": first_line.brand,
                        "model": first_line.model,
                    }
                )
            if order.department:
                metadata_defaults.setdefault("department", order.department)
            try:
                validated_metadata = prepare_stock_metadata(
                    category_value,
                    data.get("metadata"),
                    defaults=metadata_defaults,
                    include_assignment_fields=False,
                )
            except ValueError as exc:
                return json_error(str(exc)), 400

        created_stock_items: list[StockItem] = []
        if action_key == "stok":
            remaining_quantity = min(requested_quantity, total_quantity)
            lines_to_remove: list[RequestLine] = []
            for line in target_lines:
                if remaining_quantity <= 0:
                    break
                available_quantity = max(0, line.quantity)
                if available_quantity <= 0:
                    continue
                fulfill_quantity = min(available_quantity, remaining_quantity)
                if fulfill_quantity <= 0:
                    continue
                created_stock_items.append(
                    create_stock_item_from_request_line(
                        order,
                        line,
                        quantity=fulfill_quantity,
                        note=note,
                        actor=actor,
                        category=category_value,
                        metadata=validated_metadata,
                    )
                )
                processed_quantity += fulfill_quantity
                remaining_quantity -= fulfill_quantity
                if fulfill_quantity >= available_quantity:
                    lines_to_remove.append(line)
                else:
                    line.quantity = available_quantity - fulfill_quantity

            for line in lines_to_remove:
                if line in order.lines:
                    order.lines.remove(line)
                db.session.delete(line)

            if processed_quantity <= 0:
                return json_error("İşlem yapılacak geçerli miktar bulunamadı."), 400
        else:
            processed_quantity = requested_quantity

        if action_key == "stok":
            remaining_total = sum(line.quantity for line in order.lines)
            target_group_key = "kapandi" if remaining_total <= 0 else "acik"
            action_label = "Talep stok girişiyle kapandı"
        else:
            target_group_key = "iptal"
            action_label = "Talep iptal edildi"

        target_group = get_request_group_by_key(target_group_key)
        if target_group:
            order.group = target_group

        db.session.flush()

        record_activity(
            area="talep",
            action=action_label,
            description=note,
            actor=actor,
            metadata={
                "order_id": order.id,
                "order_no": order.order_no,
                "quantity": quantity,
                "target_group": order.group.key if order.group else None,
            },
        )

        db.session.commit()

        fresh_order = get_request_order_with_relations(order.id)
        payload = serialize_request_order(fresh_order)
        message = f"{payload['order_no']} numaralı talep için işlem kaydedildi."
        response_payload: dict[str, Any] = {"order": payload, "message": message}
        if created_stock_items:
            response_payload["stock_items"] = [
                serialize_stock_item(get_stock_item_with_relations(item.id))
                for item in created_stock_items
                if item
            ]
        return jsonify(response_payload)

    @app.post("/api/catalog/products")
    def create_catalog_product():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        try:
            usage_area_id = int(data.get("usage_area_id"))
            license_name_id = int(data.get("license_name_id"))
            info_category_id = int(data.get("info_category_id"))
            factory_id = int(data.get("factory_id"))
            hardware_type_id = int(data.get("hardware_type_id"))
            brand_id = int(data.get("brand_id"))
            model_id = int(data.get("model_id"))
        except (TypeError, ValueError):
            return json_error("Lütfen tüm alanları seçin."), 400

        usage_area = UsageArea.query.get(usage_area_id)
        license_name = LicenseName.query.get(license_name_id)
        info_category = InfoCategory.query.get(info_category_id)
        factory = Factory.query.get(factory_id)
        hardware_type = HardwareType.query.get(hardware_type_id)
        brand = Brand.query.get(brand_id)
        model = HardwareModel.query.get(model_id)

        if not all([usage_area, license_name, info_category, factory, hardware_type, brand, model]):
            return json_error("Seçilen kayıtlar doğrulanamadı."), 400

        entry = ProductCatalogEntry(
            usage_area=usage_area,
            license_name=license_name,
            info_category=info_category,
            factory=factory,
            hardware_type=hardware_type,
            brand=brand,
            model=model,
        )
        db.session.add(entry)
        db.session.flush()

        record_activity(
            area="urun",
            action="Ürün taslağı kaydedildi",
            description=f"{brand.name} {model.name} için taslak oluşturuldu.",
            metadata={
                "entry_id": entry.id,
                "brand": brand.name,
                "model": model.name,
                "factory": factory.name,
            },
        )

        db.session.commit()

        fresh_entry = (
            ProductCatalogEntry.query.options(
                joinedload(ProductCatalogEntry.usage_area),
                joinedload(ProductCatalogEntry.license_name),
                joinedload(ProductCatalogEntry.info_category),
                joinedload(ProductCatalogEntry.factory),
                joinedload(ProductCatalogEntry.hardware_type),
                joinedload(ProductCatalogEntry.brand),
                joinedload(ProductCatalogEntry.model),
            )
            .filter_by(id=entry.id)
            .first()
        )

        payload = serialize_catalog_entry(fresh_entry)
        return (
            jsonify(
                {
                    "entry": payload,
                    "message": "Ürün taslağı başarıyla kaydedildi.",
                }
            ),
            201,
        )

    @app.delete("/api/catalog/products/<int:entry_id>")
    def delete_catalog_product(entry_id: int):
        entry = (
            ProductCatalogEntry.query.options(
                joinedload(ProductCatalogEntry.brand),
                joinedload(ProductCatalogEntry.model),
            )
            .filter_by(id=entry_id)
            .first()
        )
        if entry is None:
            return jsonify({"error": "Kayıt bulunamadı."}), 404

        brand_name = entry.brand.name if entry.brand else ""
        model_name = entry.model.name if entry.model else ""

        db.session.delete(entry)

        record_activity(
            area="urun",
            action="Ürün taslağı silindi",
            description=f"{brand_name} {model_name} taslağı kaldırıldı.",
            metadata={"entry_id": entry_id},
        )

        db.session.commit()
        return ("", 204)

    @app.get("/api/license-names")
    def list_license_names():
        names = [
            license_name.to_dict()
            for license_name in LicenseName.query.order_by(LicenseName.name)
        ]
        return jsonify({"items": names})

    @app.route("/talep-takip")
    def talep_takip():
        payload = load_request_groups()

        return render_template(
            "talep_takip.html",
            active_page="talep_takip",
            **payload,
        )

    @app.route("/islem-kayitlari")
    def activity_logs():
        if not has_system_role(get_active_user(), "admin"):
            flash("İşlem kayıtlarını görüntülemek için yetkiniz yok.", "danger")
            return redirect(url_for("index"))
        logs = load_activity_logs()
        unique_areas = sorted({log.get("area", "") for log in logs if log.get("area")})
        default_area = "kullanici" if any(log.get("area") == "kullanici" for log in logs) else "all"
        return render_template(
            "activity_logs.html",
            active_page="activity_logs",
            logs=logs,
            log_areas=unique_areas,
            default_activity_area=default_area,
        )

    return app


def get_database_path() -> Path:
    configured = current_app.config.get("DATABASE_PATH")
    if configured:
        return Path(configured)

    database_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if database_uri.startswith("sqlite:///"):
        return Path(database_uri.replace("sqlite:///", "", 1))

    raise RuntimeError("Veritabanı yolu yapılandırmada bulunamadı.")


def load_inventory_payload() -> dict:
    items = (
        InventoryItem.query.options(
            joinedload(InventoryItem.factory),
            joinedload(InventoryItem.hardware_type),
            joinedload(InventoryItem.brand),
            joinedload(InventoryItem.model),
            joinedload(InventoryItem.responsible_user),
            joinedload(InventoryItem.events),
            joinedload(InventoryItem.licenses),
        )
        .order_by(InventoryItem.inventory_no)
        .all()
    )

    payload = [serialize_inventory_item(item) for item in items]
    visible_items = [item for item in payload if item.get("status") != "stokta"]
    faulty_count = sum(1 for item in visible_items if item["status"] == "arizali")
    departments_set: set[str] = {
        item["department"] for item in visible_items if item.get("department")
    }

    factories = [factory.to_dict() for factory in Factory.query.order_by(Factory.name)]
    hardware_types = [ht.to_dict() for ht in HardwareType.query.order_by(HardwareType.name)]
    brand_models = [
        brand.to_dict(include_models=True)
        for brand in Brand.query.options(joinedload(Brand.models)).order_by(Brand.name)
    ]
    users = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "department": user.department,
        }
        for user in User.query.order_by(User.first_name, User.last_name)
    ]
    departments_set.update({user["department"] for user in users if user["department"]})
    departments = sorted(departments_set)

    status_choices = [
        {"value": "aktif", "label": "Aktif"},
        {"value": "beklemede", "label": "Beklemede"},
        {"value": "arizali", "label": "Arızalı"},
        {"value": "hurda", "label": "Hurdaya Ayrıldı"},
    ]

    return {
        "inventory_items": visible_items,
        "inventory_faulty_count": faulty_count,
        "factories": factories,
        "hardware_types": hardware_types,
        "brand_models": brand_models,
        "users": users,
        "departments": departments,
        "status_choices": status_choices,
    }


def load_printer_payload() -> dict[str, Any]:
    printer_type = (
        HardwareType.query.filter(func.lower(HardwareType.name) == "yazıcı").first()
    )

    query = InventoryItem.query.options(
        joinedload(InventoryItem.factory),
        joinedload(InventoryItem.hardware_type),
        joinedload(InventoryItem.brand),
        joinedload(InventoryItem.model),
        joinedload(InventoryItem.responsible_user),
        joinedload(InventoryItem.events),
        joinedload(InventoryItem.licenses),
    ).order_by(InventoryItem.inventory_no)

    if printer_type is None:
        items: list[InventoryItem] = []
    else:
        items = query.filter(InventoryItem.hardware_type_id == printer_type.id).all()

    printers = [serialize_inventory_item(item) for item in items]
    printers = [printer for printer in printers if printer.get("status") != "stokta"]
    faulty_count = sum(1 for printer in printers if printer["status"] == "arizali")

    status_choices = [
        {"value": "aktif", "label": "Aktif"},
        {"value": "beklemede", "label": "Beklemede"},
        {"value": "arizali", "label": "Arızalı"},
        {"value": "hurda", "label": "Hurdaya Ayrıldı"},
    ]
    status_labels = {choice["value"]: choice["label"] for choice in status_choices}

    status_summary = [
        {
            "value": value,
            "label": status_labels[value],
            "count": sum(1 for printer in printers if printer["status"] == value),
        }
        for value in status_labels
    ]

    factories = [factory.to_dict() for factory in Factory.query.order_by(Factory.name)]
    usage_areas = [ua.to_dict() for ua in UsageArea.query.order_by(UsageArea.name)]
    brand_models = [
        brand.to_dict(include_models=True)
        for brand in Brand.query.options(joinedload(Brand.models)).order_by(Brand.name)
    ]
    users = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "department": user.department,
        }
        for user in User.query.order_by(User.first_name, User.last_name)
    ]

    inventory_catalog = [
        {
            "id": item.id,
            "inventory_no": item.inventory_no,
            "label": " · ".join(
                filter(
                    None,
                    [
                        item.inventory_no,
                        item.computer_name,
                        item.hardware_type.name if item.hardware_type else "",
                    ],
                )
            ),
        }
        for item in InventoryItem.query.options(
            joinedload(InventoryItem.hardware_type)
        ).order_by(InventoryItem.inventory_no)
        if (item.status or "").lower() != "stokta"
    ]

    return {
        "printers": printers,
        "printer_faulty_count": faulty_count,
        "printer_status_summary": status_summary,
        "printer_status_labels": status_labels,
        "factories": factories,
        "usage_areas": usage_areas,
        "brand_models": brand_models,
        "users": users,
        "inventory_catalog": inventory_catalog,
        "status_choices": status_choices,
    }


def normalize_stock_category(value: str | None, fallback: str = "envanter") -> str:
    if not value:
        return fallback
    normalized = value.strip().lower()
    return normalized if normalized in STOCK_CATEGORY_LABELS else fallback


def determine_stock_category_from_inventory(
    item: InventoryItem | None, fallback: str = "envanter"
) -> str:
    if not item:
        return fallback
    hardware_name = (item.hardware_type.name if item.hardware_type else "") or ""
    if "yazıcı" in hardware_name.lower():
        return "yazici"
    return fallback


def serialize_stock_item(stock_item: StockItem) -> dict[str, Any]:
    item = stock_item.inventory_item
    license_record = stock_item.license
    metadata = stock_item.metadata_payload or {}

    category_value = normalize_stock_category(stock_item.category)
    if category_value == "envanter" and item:
        category_value = determine_stock_category_from_inventory(item, category_value)
    if category_value == "envanter" and stock_item.source_type == "license":
        category_value = "lisans"
    if category_value == "envanter" and stock_item.source_type == "request":
        category_value = "talep"

    status_value = normalize_stock_status(stock_item.status)
    source_type = (stock_item.source_type or "manual").lower()
    source_label = STOCK_SOURCE_LABELS.get(source_type, STOCK_SOURCE_LABELS["manual"])

    created_display = (
        stock_item.created_at.strftime("%d.%m.%Y %H:%M")
        if stock_item.created_at
        else ""
    )
    updated_display = (
        stock_item.updated_at.strftime("%d.%m.%Y %H:%M")
        if stock_item.updated_at
        else created_display
    )

    hardware_type = (
        item.hardware_type.name if item and item.hardware_type else metadata.get("hardware_type", "")
    )
    brand_name = item.brand.name if item and item.brand else metadata.get("brand", "")
    model_name = item.model.name if item and item.model else metadata.get("model", "")

    search_tokens = [
        stock_item.title,
        stock_item.reference_code,
        STOCK_CATEGORY_LABELS.get(category_value, category_value.capitalize()),
        STOCK_STATUS_LABELS.get(status_value, status_value.capitalize()),
        source_label,
        metadata.get("factory"),
        metadata.get("department"),
        hardware_type,
        brand_name,
        model_name,
        metadata.get("license_key"),
        metadata.get("request_no"),
        metadata.get("responsible"),
    ]
    if item:
        search_tokens.extend(
            [
                item.inventory_no,
                item.department,
                item.factory.name if item.factory else "",
                hardware_type,
                item.serial_no,
                item.ifs_no,
            ]
        )
    if license_record:
        search_tokens.extend([license_record.name, license_record.status])

    allow_operations = status_value == "stokta"

    return {
        "id": stock_item.id,
        "title": stock_item.title,
        "category": category_value,
        "category_label": STOCK_CATEGORY_LABELS.get(
            category_value, category_value.capitalize()
        ),
        "quantity": stock_item.quantity,
        "unit": stock_item.unit or metadata.get("unit") or "adet",
        "reference_code": stock_item.reference_code or "",
        "status": status_value,
        "status_label": STOCK_STATUS_LABELS.get(
            status_value, status_value.capitalize()
        ),
        "status_class": STOCK_STATUS_CLASSES.get(status_value, "status-stock"),
        "source_type": source_type,
        "source_label": source_label,
        "note": stock_item.note or "",
        "metadata": metadata,
        "inventory_id": item.id if item else None,
        "inventory_no": item.inventory_no if item else "",
        "hardware_type": hardware_type,
        "brand": brand_name,
        "model": model_name,
        "license_id": license_record.id if license_record else None,
        "license_name": license_record.name if license_record else metadata.get("license_name"),
        "created_display": created_display,
        "updated_display": updated_display,
        "search_index": " ".join(filter(None, search_tokens)).lower(),
        "allow_operations": allow_operations,
    }


def serialize_stock_log(log: StockLog) -> dict[str, Any]:
    item = log.stock_item
    status_value = normalize_stock_status(item.status if item else "stokta")
    return {
        "id": log.id,
        "stock_item_id": item.id if item else None,
        "title": item.title if item else "",
        "action": log.action,
        "action_type": log.action_type,
        "performed_by": log.performed_by,
        "quantity_change": log.quantity_change,
        "note": log.note or "",
        "status": status_value,
        "status_label": STOCK_STATUS_LABELS.get(status_value, status_value.capitalize()),
        "status_class": STOCK_STATUS_CLASSES.get(status_value, "status-stock"),
        "created_display": log.created_at.strftime("%d.%m.%Y %H:%M"),
        "metadata": log.metadata_payload or {},
    }


def load_stock_payload() -> dict[str, Any]:
    items = (
        StockItem.query.options(
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.hardware_type),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.factory),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.brand),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.model),
            joinedload(StockItem.license),
            joinedload(StockItem.logs),
        )
        .order_by(StockItem.created_at.desc())
        .all()
    )

    stock_items = [serialize_stock_item(item) for item in items]
    category_counts = Counter(item["category"] for item in stock_items)
    status_counts = Counter(item["status"] for item in stock_items)
    faulty_count = status_counts.get("arizali", 0)

    assignment_map: dict[str, list[dict[str, Any]]] = {}
    for item in stock_items:
        if item.get("status") != "devredildi":
            continue
        responsible = (item.get("metadata") or {}).get("responsible")
        if not responsible:
            continue
        assignment_map.setdefault(responsible, []).append(
            {
                "id": item["id"],
                "title": item["title"],
                "hardware_type": item.get("hardware_type") or item.get("title"),
                "category_label": item.get("category_label"),
                "quantity": item.get("quantity"),
                "status": item.get("status"),
                "status_label": item.get("status_label"),
                "updated_display": item.get("updated_display"),
            }
        )

    user_assignments = [
        {
            "responsible": name,
            "items": sorted(entries, key=lambda payload: payload.get("updated_display") or "", reverse=True),
        }
        for name, entries in sorted(assignment_map.items())
    ]

    categories = [
        {
            "value": key,
            "label": STOCK_CATEGORY_LABELS[key],
            "count": category_counts.get(key, 0),
        }
        for key in STOCK_CATEGORY_LABELS
    ]

    status_summary = [
        {
            "value": key,
            "label": STOCK_STATUS_LABELS[key],
            "count": status_counts.get(key, 0),
        }
        for key in STOCK_STATUS_LABELS
    ]

    logs = (
        StockLog.query.options(joinedload(StockLog.stock_item))
        .order_by(StockLog.created_at.desc())
        .limit(40)
        .all()
    )

    support_options = build_stock_support_options()

    return {
        "stock_items": stock_items,
        "stock_logs": [serialize_stock_log(log) for log in logs],
        "stock_categories": categories,
        "stock_status_summary": status_summary,
        "stock_faulty_count": faulty_count,
        "stock_metadata_config": STOCK_METADATA_FIELDS,
        "stock_support_options": support_options,
        "stock_user_assignments": user_assignments,
    }


def normalize_stock_status(value: str | None, fallback: str = "stokta") -> str:
    if not value:
        return fallback
    normalized = value.strip().lower()
    return normalized if normalized in STOCK_STATUS_LABELS else fallback


def load_scrap_inventory_payload() -> dict[str, Any]:
    items = (
        InventoryItem.query.options(
            joinedload(InventoryItem.factory),
            joinedload(InventoryItem.hardware_type),
            joinedload(InventoryItem.brand),
            joinedload(InventoryItem.model),
            joinedload(InventoryItem.responsible_user),
            joinedload(InventoryItem.events),
        )
        .filter(func.lower(InventoryItem.status) == "hurda")
        .order_by(InventoryItem.updated_at.desc(), InventoryItem.inventory_no)
        .all()
    )

    scrap_items = [serialize_inventory_item(item) for item in items]

    return {
        "scrap_items": scrap_items,
        "scrap_count": len(scrap_items),
    }


def load_information_entry(entry_id: int) -> InfoEntry | None:
    return (
        InfoEntry.query.options(
            joinedload(InfoEntry.category),
            joinedload(InfoEntry.attachments),
        )
        .filter_by(id=entry_id)
        .first()
    )


def load_information_payload() -> dict[str, Any]:
    entries = (
        InfoEntry.query.options(joinedload(InfoEntry.category))
        .order_by(InfoEntry.created_at.desc())
        .all()
    )
    categories = [
        category.to_dict() for category in InfoCategory.query.order_by(InfoCategory.name)
    ]
    return {
        "info_entries": entries,
        "categories": categories,
        "info_count": len(entries),
    }


def save_information_file(file: FileStorage | None) -> tuple[str, str] | None:
    if file is None or not file.filename:
        return None

    original_name = secure_filename(file.filename)
    if not original_name:
        return None

    extension = Path(original_name).suffix
    unique_name = f"{uuid4().hex}{extension}" if extension else uuid4().hex
    upload_dir: Path = current_app.config["INFO_UPLOAD_DIR"]
    target = upload_dir / unique_name
    file.save(target)
    return unique_name, original_name


def save_information_image(file: FileStorage | None) -> str | None:
    saved = save_information_file(file)
    return saved[0] if saved else None


def remove_information_file(filename: str | None) -> None:
    if not filename:
        return

    upload_dir: Path = current_app.config["INFO_UPLOAD_DIR"]
    target = upload_dir / filename
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def remove_information_image(filename: str | None) -> None:
    remove_information_file(filename)


def serialize_inventory_item(item: InventoryItem) -> dict[str, Any]:
    responsible = (
        f"{item.responsible_user.first_name} {item.responsible_user.last_name}"
        if item.responsible_user
        else "Henüz atanmamış"
    )
    brand_name = item.brand.name if item.brand else ""
    model_name = item.model.name if item.model else ""
    status_value = (item.status or "aktif").lower()

    history = [
        {
            "id": event.id,
            "event_type": event.event_type,
            "performed_by": event.performed_by,
            "performed_at": event.performed_at.strftime("%d.%m.%Y %H:%M"),
            "note": event.note,
        }
        for event in item.events
    ]

    licenses = [serialize_license_record(license) for license in item.licenses]

    search_tokens = [
        item.inventory_no,
        item.computer_name,
        item.factory.name if item.factory else "",
        item.department,
        item.hardware_type.name if item.hardware_type else "",
        responsible,
        brand_name,
        model_name,
        item.serial_no,
        item.ifs_no,
    ]

    return {
        "id": item.id,
        "inventory_no": item.inventory_no,
        "computer_name": item.computer_name,
        "factory": item.factory.name if item.factory else "",
        "factory_id": item.factory_id,
        "department": item.department,
        "hardware_type": item.hardware_type.name if item.hardware_type else "",
        "hardware_type_id": item.hardware_type_id,
        "responsible": responsible,
        "responsible_user_id": item.responsible_user_id,
        "brand": brand_name,
        "brand_id": item.brand_id,
        "model": model_name,
        "model_id": item.model_id,
        "serial_no": item.serial_no,
        "ifs_no": item.ifs_no,
        "related_machine_no": item.related_machine_no,
        "machine_no": item.machine_no,
        "ip_address": item.related_machine_no,
        "mac_address": item.machine_no,
        "note": item.note,
        "status": status_value,
        "history": history,
        "licenses": licenses,
        "search_index": " ".join(filter(None, search_tokens)).lower(),
    }


def serialize_license_record(license: InventoryLicense) -> dict[str, Any]:
    item = license.item
    responsible_user = item.responsible_user if item else None
    responsible_name = (
        f"{responsible_user.first_name} {responsible_user.last_name}"
        if responsible_user
        else ""
    )
    email = responsible_user.email if responsible_user else ""
    department = responsible_user.department if responsible_user else ""
    inventory_no = item.inventory_no if item else ""
    computer_name = item.computer_name if item else ""
    hardware_type_name = item.hardware_type.name if item and item.hardware_type else ""
    inventory_label = inventory_no
    if inventory_no:
        if computer_name:
            inventory_label = f"{inventory_no} · {computer_name}"
        elif hardware_type_name:
            inventory_label = f"{inventory_no} · {hardware_type_name}"
    factory_name = item.factory.name if item and item.factory else ""
    ifs_no = item.ifs_no if item else ""
    status_value = (license.status or "aktif").lower()
    status_label = LICENSE_STATUS_LABELS.get(status_value, status_value.capitalize())
    display_name, key = split_license_name(license.name)

    history: list[dict[str, Any]] = []
    if item and item.events:
        for event in sorted(item.events, key=lambda e: e.performed_at, reverse=True):
            history.append(
                {
                    "title": event.event_type,
                    "actor": event.performed_by,
                    "note": event.note or "",
                    "performed_at": event.performed_at.strftime("%d.%m.%Y %H:%M"),
                }
            )

    search_tokens = [
        display_name or license.name,
        key,
        responsible_name,
        email,
        department,
        inventory_no,
        computer_name,
        factory_name,
        status_label,
    ]

    return {
        "id": license.id,
        "display_name": display_name or license.name,
        "key": key,
        "raw_name": license.name,
        "status": status_value,
        "status_label": status_label,
        "responsible_id": responsible_user.id if responsible_user else None,
        "responsible_name": responsible_name or "Atama bekliyor",
        "responsible_department": department,
        "email": email,
        "inventory_id": item.id if item else None,
        "inventory_no": inventory_no,
        "inventory_label": inventory_label or inventory_no,
        "computer_name": computer_name,
        "factory": factory_name,
        "department": item.department if item else "",
        "ifs_no": ifs_no,
        "history": history,
        "search_index": " ".join(token for token in search_tokens if token).lower(),
    }


def load_license_payload() -> dict[str, Any]:
    licenses = (
        InventoryLicense.query.options(
            joinedload(InventoryLicense.item)
            .joinedload(InventoryItem.responsible_user),
            joinedload(InventoryLicense.item).joinedload(InventoryItem.hardware_type),
            joinedload(InventoryLicense.item).joinedload(InventoryItem.factory),
            joinedload(InventoryLicense.item).joinedload(InventoryItem.events),
        )
        .order_by(InventoryLicense.id)
        .all()
    )

    license_records = [serialize_license_record(license) for license in licenses]

    users = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "department": user.department or "",
        }
        for user in User.query.order_by(User.first_name, User.last_name)
    ]

    inventory_options = [
        {
            "id": item.id,
            "inventory_no": item.inventory_no,
            "label": (
                f"{item.inventory_no} · {item.computer_name}"
                if item.computer_name
                else (
                    f"{item.inventory_no} · {item.hardware_type.name}"
                    if item.hardware_type
                    else item.inventory_no
                )
            ),
            "ifs_no": item.ifs_no or "",
            "department": item.department or "",
        }
        for item in InventoryItem.query.options(
            joinedload(InventoryItem.hardware_type)
        ).order_by(InventoryItem.inventory_no)
        if (item.status or "").lower() != "stokta"
    ]

    status_counts = {
        "total": len(license_records),
        "active": sum(1 for record in license_records if record["status"] == "aktif"),
        "passive": sum(1 for record in license_records if record["status"] == "pasif"),
    }

    return {
        "license_records": license_records,
        "license_users": users,
        "license_inventory_options": inventory_options,
        "license_names": [
            ln.to_dict() for ln in LicenseName.query.order_by(LicenseName.name)
        ],
        "license_status_counts": status_counts,
    }


def serialize_request_order(order: RequestOrder) -> dict[str, Any]:
    opened_display = order.opened_at.strftime("%d.%m.%Y %H:%M")
    lines_payload: list[dict[str, Any]] = []
    search_tokens = [order.order_no, order.requested_by, order.department, opened_display]

    for line in order.lines:
        category_value = normalize_stock_category(line.category, fallback="envanter")
        line_payload = {
            "id": line.id,
            "hardware_type": line.hardware_type,
            "brand": line.brand,
            "model": line.model,
            "quantity": line.quantity,
            "note": line.note,
            "opened_display": opened_display,
            "category": category_value,
            "category_label": STOCK_CATEGORY_LABELS.get(
                category_value, category_value.capitalize()
            ),
        }
        lines_payload.append(line_payload)
        search_tokens.extend(
            [
                line_payload["hardware_type"],
                line_payload["brand"],
                line_payload["model"],
                line_payload["category_label"],
                line_payload.get("note"),
            ]
        )

    return {
        "id": order.id,
        "order_no": order.order_no,
        "requested_by": order.requested_by,
        "department": order.department,
        "opened_display": opened_display,
        "lines": lines_payload,
        "item_count": len(lines_payload),
        "total_quantity": sum(line["quantity"] for line in lines_payload),
        "search_index": " ".join(token for token in search_tokens if token).lower(),
        "group_key": order.group.key if order.group else None,
    }


def serialize_activity_log(log: ActivityLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "area": log.area,
        "action": log.action,
        "description": log.description,
        "actor": log.actor,
        "metadata": log.metadata_payload or {},
        "created_display": log.created_at.strftime("%d.%m.%Y %H:%M"),
    }


def serialize_catalog_entry(entry: ProductCatalogEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "usage_area": entry.usage_area.name if entry.usage_area else "",
        "license_name": entry.license_name.name if entry.license_name else "",
        "info_category": entry.info_category.name if entry.info_category else "",
        "factory": entry.factory.name if entry.factory else "",
        "hardware_type": entry.hardware_type.name if entry.hardware_type else "",
        "brand": entry.brand.name if entry.brand else "",
        "model": entry.model.name if entry.model else "",
        "created_display": entry.created_at.strftime("%d.%m.%Y %H:%M"),
    }


def load_request_groups() -> dict[str, Any]:
    request_groups_payload: list[dict[str, Any]] = []
    groups = (
        RequestGroup.query.options(
            joinedload(RequestGroup.orders).joinedload(RequestOrder.lines)
        )
        .order_by(RequestGroup.id)
        .all()
    )

    for group in groups:
        orders_payload = [serialize_request_order(order) for order in group.orders]
        request_groups_payload.append(
            {
                "key": group.key,
                "label": group.label,
                "description": group.description,
                "empty_message": group.empty_message,
                "orders": orders_payload,
            }
        )

    hardware_catalog = {
        "types": [ht.name for ht in HardwareType.query.order_by(HardwareType.name)],
        "brands": [brand.name for brand in Brand.query.order_by(Brand.name)],
        "models": [model.name for model in HardwareModel.query.order_by(HardwareModel.name)],
    }

    return {
        "request_groups": request_groups_payload,
        "hardware_catalog": hardware_catalog,
        "stock_metadata_config": STOCK_METADATA_FIELDS,
        "stock_support_options": build_stock_support_options(),
        "stock_category_labels": STOCK_CATEGORY_LABELS,
    }


def get_inventory_item_with_relations(item_id: int) -> InventoryItem | None:
    return (
        InventoryItem.query.options(
            joinedload(InventoryItem.factory),
            joinedload(InventoryItem.hardware_type),
            joinedload(InventoryItem.brand),
            joinedload(InventoryItem.model),
            joinedload(InventoryItem.responsible_user),
            joinedload(InventoryItem.events),
            joinedload(InventoryItem.licenses),
        ).get(item_id)
    )


def get_stock_item_with_relations(item_id: int) -> StockItem | None:
    return (
        StockItem.query.options(
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.hardware_type),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.factory),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.brand),
            joinedload(StockItem.inventory_item).joinedload(InventoryItem.model),
            joinedload(StockItem.license),
            joinedload(StockItem.logs),
        )
        .filter_by(id=item_id)
        .first()
    )


def get_request_order_with_relations(order_id: int) -> RequestOrder | None:
    return (
        RequestOrder.query.options(
            joinedload(RequestOrder.group),
            joinedload(RequestOrder.lines),
        )
        .filter_by(id=order_id)
        .first()
    )


def get_request_group_by_key(key: str) -> RequestGroup | None:
    normalized = (key or "").strip().lower()
    if not normalized:
        return None
    return RequestGroup.query.filter(func.lower(RequestGroup.key) == normalized).first()


def add_inventory_event(
    item: InventoryItem, event_type: str, note: str | None = None, performed_by: str = DEFAULT_EVENT_ACTOR
) -> InventoryEvent:
    event = InventoryEvent(
        item=item,
        event_type=event_type,
        performed_by=performed_by,
        note=note or None,
    )
    db.session.add(event)
    record_activity(
        area="envanter",
        action=event_type,
        description=note,
        actor=performed_by,
        metadata={
            "inventory_id": item.id,
            "inventory_no": item.inventory_no,
            "status": item.status,
        },
    )
    return event


def record_stock_log(
    stock_item: StockItem,
    action: str,
    *,
    action_type: str = "info",
    performed_by: str | None = None,
    quantity_change: int = 0,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> StockLog:
    actor = (performed_by or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR
    log = StockLog(
        stock_item=stock_item,
        action=action,
        action_type=action_type,
        performed_by=actor,
        quantity_change=quantity_change,
        note=note or None,
    )
    log.metadata_payload = metadata or None
    db.session.add(log)

    activity_metadata = {
        "stock_item_id": stock_item.id,
        "stock_item_title": stock_item.title,
        "stock_item_status": stock_item.status,
    }
    if metadata:
        activity_metadata.update(metadata)

    record_activity(
        area="stok",
        action=action,
        description=note or stock_item.title,
        actor=actor,
        metadata=activity_metadata,
    )
    return log


def build_inventory_stock_metadata(item: InventoryItem) -> dict[str, str]:
    return {
        "inventory_no": item.inventory_no or "",
        "computer_name": item.computer_name or "",
        "hostname": item.computer_name or "",
        "factory": item.factory.name if item.factory else "",
        "department": item.department or "",
        "hardware_type": item.hardware_type.name if item.hardware_type else "",
        "brand": item.brand.name if item.brand else "",
        "model": item.model.name if item.model else "",
        "serial_no": item.serial_no or "",
        "ifs_no": item.ifs_no or "",
        "ip_address": item.related_machine_no or "",
        "mac_address": item.machine_no or "",
        "responsible": (
            f"{item.responsible_user.first_name} {item.responsible_user.last_name}"
            if item.responsible_user
            else ""
        ),
    }


def create_stock_item_from_inventory(
    item: InventoryItem,
    *,
    note: str | None = None,
    actor: str = DEFAULT_EVENT_ACTOR,
) -> StockItem:
    title_parts = [
        item.brand.name if item.brand else "",
        item.model.name if item.model else "",
    ]
    title = " ".join(part for part in title_parts if part).strip()
    if not title:
        title = item.inventory_no or "Envanter"

    stock_item = StockItem(
        source_type="inventory",
        inventory_item=item,
        reference_code=item.inventory_no,
        title=title,
        category=determine_stock_category_from_inventory(item),
        quantity=1,
        status="stokta",
        note=note or None,
    )
    metadata_payload = build_inventory_stock_metadata(item)
    stock_item.metadata_payload = {key: value for key, value in metadata_payload.items() if value}
    db.session.add(stock_item)
    db.session.flush()
    record_stock_log(
        stock_item,
        "Stok girişi",
        action_type="in",
        performed_by=actor,
        quantity_change=1,
        note=note,
        metadata={"inventory_no": item.inventory_no},
    )
    return stock_item


def create_stock_item_from_license(
    license: InventoryLicense,
    *,
    note: str | None = None,
    actor: str = DEFAULT_EVENT_ACTOR,
) -> StockItem:
    display_name, key = split_license_name(license.name)
    title = display_name or license.name
    stock_item = StockItem(
        source_type="license",
        license=license,
        reference_code=license.name,
        title=title or "Lisans",
        category="lisans",
        quantity=1,
        status="stokta",
        note=note or None,
    )
    associated_item = license.item
    stock_item.metadata_payload = {
        "license_key": key,
        "license_name": title,
        "inventory_no": associated_item.inventory_no if associated_item else "",
        "department": associated_item.department if associated_item else "",
        "factory": associated_item.factory.name if associated_item and associated_item.factory else "",
    }
    db.session.add(stock_item)
    db.session.flush()
    record_stock_log(
        stock_item,
        "Lisans stok girişi",
        action_type="in",
        performed_by=actor,
        quantity_change=1,
        note=note,
        metadata={"license_id": license.id},
    )
    return stock_item


def create_stock_item_from_request_line(
    order: RequestOrder,
    line: RequestLine,
    *,
    quantity: int,
    note: str | None = None,
    actor: str = DEFAULT_EVENT_ACTOR,
    category: str | None = None,
    metadata: dict[str, str] | None = None,
) -> StockItem:
    title_parts = [line.brand, line.model]
    title = " ".join(part for part in title_parts if part).strip() or line.hardware_type
    category_value = normalize_stock_category(
        category or line.category,
        fallback="talep",
    )
    metadata_payload = {
        "request_no": order.order_no,
        "department": order.department,
        "hardware_type": line.hardware_type,
        "brand": line.brand,
        "model": line.model,
    }
    if metadata:
        metadata_payload.update(metadata)
    reference_code = (
        metadata_payload.get("inventory_no")
        or metadata_payload.get("license_key")
        or order.order_no
    )
    stock_item = StockItem(
        source_type="request",
        source_id=order.id,
        reference_code=reference_code,
        title=title or "Talep Öğesi",
        category=category_value,
        quantity=max(1, quantity),
        status="stokta",
        note=note or None,
    )
    stock_item.metadata_payload = metadata_payload
    db.session.add(stock_item)
    db.session.flush()
    record_stock_log(
        stock_item,
        "Talep stok girişi",
        action_type="in",
        performed_by=actor,
        quantity_change=stock_item.quantity,
        note=note,
        metadata={"request_id": order.id},
    )
    return stock_item


def parse_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def prepare_stock_metadata(
    category: str,
    payload: Any,
    *,
    defaults: dict[str, Any] | None = None,
    include_assignment_fields: bool = True,
) -> dict[str, str]:
    schema = STOCK_METADATA_FIELDS.get(category, [])
    if not include_assignment_fields:
        schema = [
            field for field in schema if not field.get("assignment_only")
        ]
    provided: dict[str, Any]
    if isinstance(payload, dict):
        provided = payload
    else:
        provided = {}
    defaults = defaults or {}
    cleaned: dict[str, str] = {}

    def normalize_value(raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw.strip()
        return str(raw).strip()

    for field in schema:
        key = field["key"]
        label = field.get("label", key.capitalize())
        value = normalize_value(provided.get(key))
        if not value:
            value = normalize_value(defaults.get(key))
        if not value and field.get("required"):
            raise ValueError(f"{label} alanı zorunludur.")
        if value:
            cleaned[key] = value

    for key, value in provided.items():
        if key in cleaned:
            continue
        normalized = normalize_value(value)
        if normalized:
            cleaned[key] = normalized

    return cleaned


def json_error(message: str) -> dict[str, str]:
    return {"error": message}


def record_activity(
    *,
    area: str,
    action: str,
    description: str | None = None,
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    log = ActivityLog(
        area=area,
        action=action,
        description=description or None,
        actor=actor or DEFAULT_EVENT_ACTOR,
        metadata_payload=metadata or None,
    )
    db.session.add(log)
    return log


def load_activity_logs(limit: int | None = None) -> list[dict[str, Any]]:
    query = ActivityLog.query.order_by(ActivityLog.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return [serialize_activity_log(log) for log in query.all()]


def load_recent_activity(limit: int = 6) -> list[dict[str, Any]]:
    allowed_areas = {"talep", "urun", "kullanici"}
    query_limit = max(limit * 4, limit)
    candidates = (
        ActivityLog.query.order_by(ActivityLog.created_at.desc())
        .limit(query_limit)
        .all()
    )
    filtered: list[dict[str, Any]] = []
    for log in candidates:
        if log.area not in allowed_areas:
            continue
        filtered.append(serialize_activity_log(log))
        if len(filtered) >= limit:
            break
    return filtered


def build_stock_support_options() -> dict[str, list[str]]:
    factory_names = [factory.name for factory in Factory.query.order_by(Factory.name)]

    department_values: set[str] = set()
    for (department,) in db.session.query(InventoryItem.department).distinct():
        if department:
            department_values.add(department)
    for (department,) in db.session.query(User.department).distinct():
        if department:
            department_values.add(department)
    department_names = sorted(department_values)

    responsible_names = [
        f"{user.first_name} {user.last_name}".strip()
        for user in User.query.order_by(User.first_name, User.last_name)
        if (user.first_name or user.last_name)
    ]

    usage_area_names = [
        usage_area.name for usage_area in UsageArea.query.order_by(UsageArea.name)
    ]
    license_name_values = [
        license_name.name for license_name in LicenseName.query.order_by(LicenseName.name)
    ]

    inventory_numbers = [
        inventory_no
        for (inventory_no,) in db.session.query(InventoryItem.inventory_no)
        .filter(InventoryItem.inventory_no.isnot(None))
        .distinct()
        .order_by(InventoryItem.inventory_no)
    ]
    return {
        "factories": factory_names,
        "departments": department_names,
        "responsibles": responsible_names,
        "usage_areas": usage_area_names,
        "license_names": license_name_values,
        "inventory_numbers": inventory_numbers,
    }


def load_admin_panel_payload() -> dict:
    users = User.query.order_by(User.first_name, User.last_name).all()

    product_options = {
        "usage_areas": [ua.to_dict() for ua in UsageArea.query.order_by(UsageArea.name)],
        "license_names": [ln.to_dict() for ln in LicenseName.query.order_by(LicenseName.name)],
        "info_categories": [ic.to_dict() for ic in InfoCategory.query.order_by(InfoCategory.name)],
        "factories": [factory.to_dict() for factory in Factory.query.order_by(Factory.name)],
        "hardware_types": [ht.to_dict() for ht in HardwareType.query.order_by(HardwareType.name)],
        "brands": [brand.to_dict() for brand in Brand.query.order_by(Brand.name)],
    }

    brand_models = [brand.to_dict(include_models=True) for brand in Brand.query.order_by(Brand.name)]
    ldap_profiles = [profile.to_dict() for profile in LdapProfile.query.order_by(LdapProfile.name)]
    catalog_entries = (
        ProductCatalogEntry.query.options(
            joinedload(ProductCatalogEntry.usage_area),
            joinedload(ProductCatalogEntry.license_name),
            joinedload(ProductCatalogEntry.info_category),
            joinedload(ProductCatalogEntry.factory),
            joinedload(ProductCatalogEntry.hardware_type),
            joinedload(ProductCatalogEntry.brand),
            joinedload(ProductCatalogEntry.model),
        )
        .order_by(ProductCatalogEntry.created_at.desc())
        .all()
    )

    return {
        "users": users,
        "product_options": product_options,
        "brand_models": brand_models,
        "ldap_profiles": ldap_profiles,
        "catalog_entries": [serialize_catalog_entry(entry) for entry in catalog_entries],
    }


def parse_option_name(payload: dict | None) -> str:
    if not payload or not isinstance(payload, dict):
        raise ValueError("Geçersiz istek gövdesi")
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("İsim alanı zorunludur")
    return name


def create_brand():
    try:
        name = parse_option_name(request.get_json())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if find_existing_by_name(Brand, name):
        return jsonify({"error": "Bu marka zaten mevcut."}), 409

    brand = Brand(name=name)
    db.session.add(brand)
    db.session.commit()
    return jsonify(brand.to_dict(include_models=True)), 201


def delete_brand(brand_id: int):
    brand = Brand.query.get(brand_id)
    if brand is None:
        return jsonify({"error": "Marka bulunamadı."}), 404

    db.session.delete(brand)
    db.session.commit()
    return ("", 204)


OPTION_MODEL_MAPPING = {
    "usage-areas": UsageArea,
    "license-names": LicenseName,
    "info-categories": InfoCategory,
    "factories": Factory,
    "hardware-types": HardwareType,
}


def seed_initial_data() -> None:
    seed_simple_users()
    seed_product_metadata()
    seed_information_entries()
    seed_inventory_data()
    seed_ldap_profiles()
    seed_request_data()
    seed_stock_data()
    db.session.commit()


def seed_simple_users() -> None:
    existing_user_count = User.query.count()

    admin_password = generate_password_hash("admin")
    created_users: list[User] = []

    admin_user = User.query.filter(func.lower(User.username) == "admin").first()

    if admin_user is None:
        admin_user = User(
            username="admin",
            first_name="Stok",
            last_name="Yöneticisi",
            email="admin@example.com",
            role="Sistem Süper Yöneticisi",
            department="Bilgi Teknolojileri",
            password_hash=admin_password,
            system_role="superadmin",
            must_change_password=True,
        )
        db.session.add(admin_user)
        created_users.append(admin_user)
    else:
        updated = False
        if not admin_user.password_hash:
            admin_user.password_hash = admin_password
            updated = True
        if not admin_user.system_role or admin_user.system_role.lower() not in {"admin", "superadmin"}:
            admin_user.system_role = "superadmin"
            updated = True
        if admin_user.must_change_password is None:
            admin_user.must_change_password = True
            updated = True
        if updated:
            created_users.append(admin_user)

    if existing_user_count:
        if created_users:
            record_activity(
                area="kullanici",
                action="Varsayılan yönetici güncellendi",
                description="Eksik yönetici hesabı oluşturuldu veya güncellendi.",
                metadata={"count": len(created_users)},
            )
        return

    default_password = generate_password_hash("Parola123!")
    demo_users = [
        User(
            username="m.cetin",
            first_name="Merve",
            last_name="Çetin",
            email="merve.cetin@example.com",
            role="Yönetici",
            department="IT Operasyon",
            password_hash=default_password,
            system_role="admin",
        ),
        User(
            username="a.kaya",
            first_name="Ahmet",
            last_name="Kaya",
            email="ahmet.kaya@example.com",
            role="Satın Alma Uzmanı",
            department="Satın Alma",
            password_hash=default_password,
            system_role="user",
        ),
        User(
            username="z.ucar",
            first_name="Zeynep",
            last_name="Uçar",
            email="zeynep.ucar@example.com",
            role="Depo Sorumlusu",
            department="Lojistik",
            password_hash=default_password,
            system_role="user",
        ),
        User(
            username="b.tan",
            first_name="Berk",
            last_name="Tan",
            email="berk.tan@example.com",
            role="Destek Uzmanı",
            department="Teknik Destek",
            password_hash=default_password,
            system_role="user",
        ),
        User(
            username="e.sonmez",
            first_name="Elif",
            last_name="Sönmez",
            email="elif.sonmez@example.com",
            role="Finans Analisti",
            department="Finans",
            password_hash=default_password,
            system_role="user",
        ),
    ]

    db.session.add_all(demo_users)
    created_users.extend(demo_users)

    record_activity(
        area="kullanici",
        action="Varsayılan kullanıcılar eklendi",
        description="Sistem başlangıç kullanıcıları oluşturuldu.",
        metadata={"count": len(created_users)},
    )


def seed_product_metadata() -> None:
    added_any = False

    if not UsageArea.query.count():
        db.session.add_all(
            UsageArea(name=name)
            for name in ["Ofis", "Saha", "Veri Merkezi", "Üretim", "Uzaktan Çalışma"]
        )
        added_any = True

    if not LicenseName.query.count():
        db.session.add_all(
            LicenseName(name=name)
            for name in [
                "Microsoft 365 Business",
                "Adobe Creative Cloud",
                "JetBrains All Products",
                "AutoCAD LT",
            ]
        )
        added_any = True

    if not InfoCategory.query.count():
        db.session.add_all(
            InfoCategory(name=name)
            for name in ["Güvenlik", "İş Uygulamaları", "İletişim", "Altyapı"]
        )
        added_any = True

    if not Factory.query.count():
        db.session.add_all(
            Factory(name=name)
            for name in ["İstanbul Merkez", "Ankara Veri Merkezi", "İzmir Üretim", "Bursa Lojistik"]
        )
        added_any = True

    if not HardwareType.query.count():
        db.session.add_all(
            HardwareType(name=name)
            for name in [
                "Laptop",
                "Masaüstü",
                "Monitör",
                "Sunucu",
                "Yazıcı",
                "Tarayıcı",
                "Tablet",
                "Aksesuar",
            ]
        )
        added_any = True

    if not Brand.query.count():
        brand_seed = {
            "Apple": ["MacBook Pro 14", "MacBook Air M2", "iMac 24"],
            "Asus": ["ZenBook 14", "ROG Zephyrus G14"],
            "Dell": ["Latitude 5440", "XPS 15", "PowerEdge R750"],
            "Fujitsu": ["fi-7160"],
            "HP": ["ProBook 450 G10", "EliteBook 840", "LaserJet Pro M404"],
            "Lenovo": ["ThinkPad X1 Carbon", "ThinkSystem SR250"],
            "Samsung": ["Galaxy Book3", "ViewFinity S8"],
        }
        for brand_name, models in brand_seed.items():
            brand = Brand(name=brand_name)
            brand.models = [HardwareModel(name=model_name) for model_name in models]
            db.session.add(brand)
        added_any = True

    if added_any:
        record_activity(
            area="urun",
            action="Ürün katalog seçenekleri hazırlandı",
            description="Varsayılan marka, model ve kullanım alanı verileri yüklendi.",
        )


def seed_information_entries() -> None:
    if InfoEntry.query.count():
        return

    categories = {category.name: category for category in InfoCategory.query.all()}

    sample_entries = [
        {
            "title": "Sosyal Mühendislik Farkındalığı",
            "category": "Güvenlik",
            "content": (
                "Şüpheli e-posta ve bağlantıları bildirmeden açmayın. Kurumsal sistemlere erişim "
                "sağlarken her zaman çok faktörlü kimlik doğrulamayı kullanın."
            ),
        },
        {
            "title": "VPN Kullanım Kılavuzu",
            "category": "Altyapı",
            "content": (
                "Uzak bağlantı kurmadan önce cihazınızın güncel olduğundan emin olun ve bağlantı "
                "esnasında sadece iş amaçlı kaynaklara erişin."
            ),
        },
        {
            "title": "Yeni Satın Alma Süreçleri",
            "category": "İş Uygulamaları",
            "content": (
                "Tüm donanım talepleri Talep Takip sayfası üzerinden açılmalı ve satın alma onayı "
                "alınmadan sipariş verilmemelidir."
            ),
        },
    ]

    created_count = 0
    for payload in sample_entries:
        category = categories.get(payload["category"])
        if not category:
            continue
        entry = InfoEntry(
            title=payload["title"],
            category=category,
            content=payload["content"],
        )
        db.session.add(entry)
        created_count += 1

    if created_count:
        record_activity(
            area="bilgi",
            action="Bilgi kayıtları oluşturuldu",
            description="Varsayılan bilgi içerikleri eklendi.",
            metadata={"count": created_count},
        )


def seed_inventory_data() -> None:
    if InventoryItem.query.count():
        return

    factories = {factory.name: factory for factory in Factory.query.all()}
    hardware_types = {ht.name: ht for ht in HardwareType.query.all()}
    users = {
        f"{user.first_name} {user.last_name}": user
        for user in User.query.all()
    }
    brands = {
        brand.name: brand
        for brand in Brand.query.options(joinedload(Brand.models)).all()
    }

    model_lookup = {}
    for brand in brands.values():
        for model in brand.models:
            model_lookup[(brand.name, model.name)] = model

    now = datetime.utcnow()

    item_primary = InventoryItem(
        inventory_no="ENV-000123",
        computer_name="PC-OFIS-01",
        factory=factories.get("İstanbul Merkez"),
        department="IT Operasyon",
        hardware_type=hardware_types.get("Laptop"),
        responsible_user=users.get("Ahmet Kaya"),
        brand=brands.get("Dell"),
        model=model_lookup.get(("Dell", "Latitude 5440")),
        serial_no="SN123456789",
        ifs_no="IFS-00045",
        related_machine_no="",
        machine_no="PC-LAP-01",
        note="IT destek ekibine teslim edildi.",
        status="aktif",
    )
    item_primary.licenses = [
        InventoryLicense(name="Office 2021 - 123456789", status="aktif"),
        InventoryLicense(name="Visio Professional - 987654321", status="aktif"),
    ]
    item_primary.events = [
        InventoryEvent(
            event_type="Stok Girişi",
            performed_by="Berk Tan",
            performed_at=now - timedelta(days=120),
            note="Merkez depoya giriş yapıldı.",
        ),
        InventoryEvent(
            event_type="Atama",
            performed_by="Merve Çetin",
            performed_at=now - timedelta(days=90),
            note="Cihaz Ahmet Kaya'ya teslim edildi.",
        ),
        InventoryEvent(
            event_type="Bakım",
            performed_by="Zeynep Uçar",
            performed_at=now - timedelta(days=15),
            note="Genel bakım ve temizlik yapıldı.",
        ),
    ]

    item_faulty = InventoryItem(
        inventory_no="ENV-000207",
        computer_name="PC-LOG-03",
        factory=factories.get("Bursa Lojistik"),
        department="Lojistik",
        hardware_type=hardware_types.get("Monitör"),
        responsible_user=users.get("Zeynep Uçar"),
        brand=brands.get("Samsung"),
        model=model_lookup.get(("Samsung", "ViewFinity S8")),
        serial_no="SN987654321",
        ifs_no="IFS-00112",
        related_machine_no="LOG-WS-04",
        machine_no="MN-LOG-03",
        note="Ekran arızası nedeniyle servise gönderilecek.",
        status="arizali",
    )
    item_faulty.licenses = [
        InventoryLicense(name="Adobe Creative Cloud - LZ-55981", status="aktif"),
    ]
    item_faulty.events = [
        InventoryEvent(
            event_type="Atama",
            performed_by="Merve Çetin",
            performed_at=now - timedelta(days=200),
            note="Zeynep Uçar'a teslim edildi.",
        ),
        InventoryEvent(
            event_type="Arıza Bildirimi",
            performed_by="Zeynep Uçar",
            performed_at=now - timedelta(days=7),
            note="Ekranda titreme sorunu bildirildi.",
        ),
        InventoryEvent(
            event_type="Tamir",
            performed_by="Servis Sağlayıcısı",
            performed_at=now - timedelta(days=2),
            note="Parça siparişi bekleniyor.",
        ),
    ]

    printer_central = InventoryItem(
        inventory_no="PRN-000444",
        computer_name="PRN-MERKEZ-01",
        factory=factories.get("İstanbul Merkez"),
        department="IT Operasyon",
        hardware_type=hardware_types.get("Yazıcı"),
        responsible_user=users.get("Merve Çetin"),
        brand=brands.get("HP"),
        model=model_lookup.get(("HP", "LaserJet Pro M404")),
        serial_no="HP444MERKEZ",
        ifs_no="IFS-00444",
        related_machine_no="10.0.0.32",
        machine_no="AA:BC:44:32:10:01",
        note="Merkez ofiste paylaşımlı yazıcı olarak kullanılıyor.",
        status="aktif",
    )
    printer_central.events = [
        InventoryEvent(
            event_type="Stok Girişi",
            performed_by="Berk Tan",
            performed_at=now - timedelta(days=60),
            note="Merkez depoya teslim alındı.",
        ),
        InventoryEvent(
            event_type="Atama",
            performed_by="Merve Çetin",
            performed_at=now - timedelta(days=58),
            note="IT Operasyon ekibine paylaşımlı olarak tanımlandı.",
        ),
        InventoryEvent(
            event_type="Bakım",
            performed_by="Servis Sağlayıcısı",
            performed_at=now - timedelta(days=12),
            note="Toner ve drum değişimi yapıldı.",
        ),
    ]

    printer_faulty = InventoryItem(
        inventory_no="PRN-000558",
        computer_name="PRN-LOG-01",
        factory=factories.get("Bursa Lojistik"),
        department="Lojistik",
        hardware_type=hardware_types.get("Yazıcı"),
        responsible_user=users.get("Zeynep Uçar"),
        brand=brands.get("HP"),
        model=model_lookup.get(("HP", "LaserJet Pro M404")),
        serial_no="HP558LOGISTIK",
        ifs_no="IFS-00558",
        related_machine_no="10.0.0.78",
        machine_no="AA:BC:55:58:10:01",
        note="Kağıt besleme ünitesinde sıkışma sorunu gözlemlendi.",
        status="arizali",
    )
    printer_faulty.events = [
        InventoryEvent(
            event_type="Atama",
            performed_by="Ahmet Kaya",
            performed_at=now - timedelta(days=180),
            note="Lojistik depoya kurulum yapıldı.",
        ),
        InventoryEvent(
            event_type="Arıza Bildirimi",
            performed_by="Zeynep Uçar",
            performed_at=now - timedelta(days=3),
            note="Kağıt besleme ünitesi kontrol edilmek üzere servis çağırıldı.",
        ),
    ]

    item_retired = InventoryItem(
        inventory_no="ENV-000318",
        computer_name="PRN-FN-02",
        factory=factories.get("Ankara Veri Merkezi"),
        department="Finans",
        hardware_type=hardware_types.get("Yazıcı"),
        responsible_user=users.get("Elif Sönmez"),
        brand=brands.get("HP"),
        model=model_lookup.get(("HP", "LaserJet Pro M404")),
        serial_no="SN564738291",
        ifs_no="IFS-00221",
        related_machine_no="10.0.0.45",
        machine_no="AA:BC:31:18:00:02",
        note="Yeni yazıcı alındığından hurdaya ayrıldı.",
        status="hurda",
    )
    item_retired.licenses = [
        InventoryLicense(name="HP ePrint Service", status="pasif"),
    ]
    item_retired.events = [
        InventoryEvent(
            event_type="Stok Girişi",
            performed_by="Ahmet Kaya",
            performed_at=now - timedelta(days=400),
            note="Depoya giriş yapıldı.",
        ),
        InventoryEvent(
            event_type="Hurdaya Ayırma",
            performed_by="Elif Sönmez",
            performed_at=now - timedelta(days=5),
            note="Yeni model yazıcı ile değiştirildi.",
        ),
    ]

    db.session.add_all([item_primary, item_faulty, printer_central, printer_faulty, item_retired])
    record_activity(
        area="envanter",
        action="Örnek envanter kayıtları yüklendi",
        description="Sistem başlangıcı için örnek envanter kayıtları oluşturuldu.",
        metadata={"count": 5},
    )


def seed_ldap_profiles() -> None:
    if LdapProfile.query.count():
        return

    db.session.add_all(
        [
            LdapProfile(
                name="Merkez AD",
                host="ad.merkez.local",
                port=389,
                base_dn="DC=merkez,DC=local",
                bind_dn="CN=ldap.service,OU=Hizmet Hesaplari,DC=merkez,DC=local",
            ),
            LdapProfile(
                name="Uzak Ofis",
                host="ldap.uzakofis.local",
                port=636,
                base_dn="DC=uzakofis,DC=local",
                bind_dn="CN=ldap.reader,OU=Servis,DC=uzakofis,DC=local",
            ),
        ]
    )


def seed_request_data() -> None:
    if RequestGroup.query.count():
        return

    now = datetime.now()

    def make_order(
        *,
        group: RequestGroup,
        order_no: str,
        requested_by: str,
        department: str,
        opened_delta: timedelta,
        lines: list[dict],
    ) -> None:
        order = RequestOrder(
            order_no=order_no,
            requested_by=requested_by,
            department=department,
            opened_at=now - opened_delta,
            group=group,
        )
        for line in lines:
            order.lines.append(
                RequestLine(
                    hardware_type=line["hardware_type"],
                    brand=line["brand"],
                    model=line["model"],
                    quantity=line["quantity"],
                    note=line.get("note"),
                )
            )
        db.session.add(order)

    open_group = RequestGroup(
        key="acik",
        label="Açık",
        description="Açıkta bekleyen talepler buradan yönetilir.",
        empty_message="Bu statüde görüntülenecek açık talep bulunmuyor.",
    )
    db.session.add(open_group)
    make_order(
        group=open_group,
        order_no="SIP-2024-015",
        requested_by="Merve Çetin",
        department="IT Operasyon",
        opened_delta=timedelta(hours=2, minutes=45),
        lines=[
            {
                "hardware_type": "Laptop",
                "brand": "Dell",
                "model": "Latitude 5440",
                "quantity": 2,
                "note": "Saha ekibi için yedek cihazlar",
            },
            {
                "hardware_type": "Monitör",
                "brand": "Dell",
                "model": "P2422H",
                "quantity": 2,
                "note": "Yeni laptoplarla birlikte gönderilecek",
            },
        ],
    )
    make_order(
        group=open_group,
        order_no="SIP-2024-018",
        requested_by="Ahmet Kaya",
        department="Satın Alma",
        opened_delta=timedelta(days=1, hours=3),
        lines=[
            {
                "hardware_type": "Yazıcı",
                "brand": "HP",
                "model": "LaserJet Pro M404",
                "quantity": 1,
                "note": "Merkez ofis için yedek yazıcı",
            }
        ],
    )

    closed_group = RequestGroup(
        key="kapandi",
        label="Kapandı",
        description="Stoklara giren ve tamamlanan taleplerin özeti.",
        empty_message="Kapanmış talep kaydı bulunmuyor.",
    )
    db.session.add(closed_group)
    make_order(
        group=closed_group,
        order_no="SIP-2024-009",
        requested_by="Zeynep Uçar",
        department="Operasyon",
        opened_delta=timedelta(days=3, hours=5),
        lines=[
            {
                "hardware_type": "Sunucu",
                "brand": "Lenovo",
                "model": "ThinkSystem SR250",
                "quantity": 1,
                "note": "Veri merkezi genişletme talebi",
            }
        ],
    )
    make_order(
        group=closed_group,
        order_no="SIP-2024-011",
        requested_by="Berk Tan",
        department="Depo",
        opened_delta=timedelta(days=2, hours=8),
        lines=[
            {
                "hardware_type": "Tarayıcı",
                "brand": "Fujitsu",
                "model": "fi-7160",
                "quantity": 3,
                "note": "Yeni şube teslim alındı",
            }
        ],
    )

    cancelled_group = RequestGroup(
        key="iptal",
        label="İptal",
        description="İptal edilen talepler ve nedenlerine buradan ulaşabilirsiniz.",
        empty_message="İptal edilmiş talep kaydı bulunmuyor.",
    )
    db.session.add(cancelled_group)
    make_order(
        group=cancelled_group,
        order_no="SIP-2024-006",
        requested_by="Elif Sönmez",
        department="Finans",
        opened_delta=timedelta(days=5, hours=4),
        lines=[
            {
                "hardware_type": "Masaüstü",
                "brand": "HP",
                "model": "ProDesk 400",
                "quantity": 1,
                "note": "Bütçe onayı alınamadı",
            }
        ],
    )
    make_order(
        group=cancelled_group,
        order_no="SIP-2024-010",
        requested_by="Pelin Arı",
        department="Pazarlama",
        opened_delta=timedelta(days=4, hours=10),
        lines=[
            {
                "hardware_type": "Tablet",
                "brand": "Apple",
                "model": "iPad Air",
                "quantity": 4,
                "note": "Etkinlik ertelendiği için iptal edildi",
            }
        ],
    )

    total_orders = sum(len(group.orders) for group in (open_group, closed_group, cancelled_group))
    record_activity(
        area="talep",
        action="Örnek talepler oluşturuldu",
        description="Açık, kapalı ve iptal statülerine örnek talepler eklendi.",
        metadata={"group_count": 3, "order_count": total_orders},
    )


def seed_stock_data() -> None:
    if StockItem.query.count():
        return

    samples = [
        {
            "title": "Yedek Laptop Adaptörü",
            "category": "envanter",
            "quantity": 8,
            "note": "Saha ekipleri için hazır tutulan adaptörler.",
            "metadata": {"department": "IT Operasyon", "factory": "İstanbul Merkez"},
        },
        {
            "title": "HP 83A Toner",
            "category": "yazici",
            "quantity": 15,
            "note": "Merkez yazıcıları için stok toner.",
            "metadata": {"department": "Lojistik", "factory": "Bursa Lojistik"},
        },
        {
            "title": "Office 2021 Pro Plus",
            "category": "lisans",
            "quantity": 4,
            "note": "Yeni cihaz kurulumu için bekleyen lisans anahtarları.",
            "metadata": {"department": "IT Operasyon"},
        },
    ]

    for sample in samples:
        stock_item = StockItem(
            source_type="manual",
            title=sample["title"],
            category=sample["category"],
            quantity=sample["quantity"],
            status="stokta",
            note=sample["note"],
        )
        stock_item.metadata_payload = sample.get("metadata")
        db.session.add(stock_item)
        db.session.flush()
        record_stock_log(
            stock_item,
            "Başlangıç stok kaydı",
            action_type="in",
            performed_by="Sistem",
            quantity_change=stock_item.quantity,
            note=sample["note"],
        )


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
