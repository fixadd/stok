from __future__ import annotations

from datetime import datetime, timedelta
from collections import Counter
from uuid import uuid4

from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from .models import (
    Brand,
    Factory,
    HardwareModel,
    HardwareType,
    InfoCategory,
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


INVENTORY_STATUSES = {"aktif", "beklemede", "arizali", "hurda"}
DEFAULT_EVENT_ACTOR = "Sistem"
LICENSE_STATUS_LABELS = {
    "aktif": "Aktif",
    "pasif": "Pasif",
    "beklemede": "Beklemede",
}


STOCK_CATEGORY_LABELS = {
    "envanter": "Envanter",
    "yazici": "Yazıcı",
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

    if altered:
        db.session.commit()


def get_active_user() -> User | None:
    user_id = session.get("active_user_id")
    user: User | None = None
    if user_id is not None:
        user = User.query.get(user_id)

    if user is None:
        user = User.query.order_by(User.id).first()
        if user is not None:
            session["active_user_id"] = user.id

    return user


def set_active_user(user: User | None) -> None:
    if user is None:
        session.pop("active_user_id", None)
    else:
        session["active_user_id"] = user.id


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

    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_user_profile_columns()
        seed_initial_data()

    @app.before_request
    def ensure_profile_context() -> None:
        if "active_user_id" in session:
            return
        user = User.query.order_by(User.id).first()
        if user is not None:
            set_active_user(user)

    @app.context_processor
    def inject_profile_preferences() -> dict[str, Any]:
        user = get_active_user()
        theme_key = "varsayilan"
        if user and user.preferred_theme in THEME_OPTIONS:
            theme_key = user.preferred_theme
        theme_meta = THEME_OPTIONS.get(theme_key, THEME_OPTIONS["varsayilan"])
        return {
            "active_user": user,
            "active_theme": theme_key,
            "active_theme_meta": theme_meta,
            "active_theme_class": f"theme-{theme_key}",
            "theme_options": THEME_OPTIONS,
        }

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
        return render_template(
            "scrap_inventory.html",
            active_page="scrap_inventory",
            **payload,
        )

    @app.route("/profil")
    def profile():
        users = User.query.order_by(User.first_name, User.last_name).all()
        profile_user = get_active_user()
        return render_template(
            "profile.html",
            active_page="profile",
            users=users,
            profile_user=profile_user,
        )

    @app.post("/profil/kullanici")
    def profile_switch_user():
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

        record_activity(
            area="profil",
            action="Şifre güncellendi",
            description=f"{user.first_name} {user.last_name}",
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
        admin_payload = load_admin_panel_payload()
        return render_template("admin_panel.html", active_page="admin_panel", **admin_payload)

    @app.post("/admin-panel/users")
    def create_user():
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()  # noqa: F841  # future integration
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        email = (request.form.get("email") or "").strip()

        if not all([username, first_name, last_name, email]):
            flash("Lütfen tüm alanları doldurun.", "danger")
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
        )
        db.session.add(user)
        db.session.flush()

        record_activity(
            area="kullanici",
            action="Kullanıcı oluşturuldu",
            description=f"{first_name} {last_name} ({username}) eklendi.",
            metadata={"user_id": user.id, "email": email},
        )

        db.session.commit()

        flash("Yeni kullanıcı başarıyla oluşturuldu.", "success")
        return redirect(url_for("admin_panel"))

    @app.post("/admin-panel/users/<int:user_id>/delete")
    def delete_user(user_id: int):
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

        db.session.delete(user)
        record_activity(
            area="kullanici",
            action="Kullanıcı silindi",
            description=description,
            metadata=metadata,
        )
        db.session.commit()

        if was_active_user:
            set_active_user(None)

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

        status = (data.get("status") or "aktif").strip().lower()
        if status not in INVENTORY_STATUSES:
            return json_error("Geçersiz durum değeri."), 400

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
            machine_no=(data.get("machine_no") or "").strip() or None,
            note=(data.get("note") or "").strip() or None,
            status=status,
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
        item.related_machine_no = (data.get("related_machine_no") or "").strip() or None
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
        item.status = "beklemede"
        add_inventory_event(item, "Stok girişi", note, performed_by=actor)
        stock_item = create_stock_item_from_inventory(item, note=note, actor=actor)
        db.session.commit()

        fresh_item = get_inventory_item_with_relations(item.id)
        payload: dict[str, Any] = {"item": serialize_inventory_item(fresh_item)}
        if stock_item:
            fresh_stock = get_stock_item_with_relations(stock_item.id)
            if fresh_stock:
                payload["stock_item"] = serialize_stock_item(fresh_stock)
                if fresh_stock.logs:
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
        quantity = parse_int_or_none(data.get("quantity")) or 1
        note = (data.get("note") or "").strip()
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR
        reference_code = (data.get("reference_code") or "").strip() or None
        unit = (data.get("unit") or "").strip() or None

        stock_item = StockItem(
            source_type="manual",
            title=title,
            category=category,
            quantity=max(1, quantity),
            status="stokta",
            reference_code=reference_code,
            unit=unit,
            note=note or None,
        )
        metadata_payload = {
            "unit": unit,
            "department": (data.get("department") or "").strip() or None,
            "factory": (data.get("factory") or "").strip() or None,
        }
        stock_item.metadata_payload = {k: v for k, v in metadata_payload.items() if v}
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

    @app.post("/api/requests")
    def create_request():
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return json_error("Geçersiz JSON gövdesi."), 400

        order_no = (data.get("order_no") or "").strip()
        requested_by = (data.get("requested_by") or "").strip()
        department = (data.get("department") or "").strip()
        group_key = (data.get("group_key") or "acik").strip().lower() or "acik"
        lines_payload = data.get("lines")

        if not order_no:
            return json_error("Sipariş numarası zorunludur."), 400
        if RequestOrder.query.filter_by(order_no=order_no).first():
            return json_error("Bu sipariş numarası zaten kayıtlı."), 409
        if not requested_by or not department:
            return json_error("Talep sahibi ve departman alanları zorunludur."), 400
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

            if not hardware_type or not brand or not model:
                return json_error(f"{index}. satır için tüm alanlar zorunludur."), 400
            if quantity <= 0:
                return json_error(f"{index}. satır için geçerli bir miktar girin."), 400

            order.lines.append(
                RequestLine(
                    hardware_type=hardware_type,
                    brand=brand,
                    model=model,
                    quantity=quantity,
                    note=note,
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
        quantity = parse_int_or_none(data.get("quantity")) or 1
        note = (data.get("note") or "").strip() or None
        actor = (data.get("performed_by") or DEFAULT_EVENT_ACTOR).strip() or DEFAULT_EVENT_ACTOR

        if action_key not in {"stok", "cancel"}:
            return json_error("Geçersiz işlem tipi."), 400

        total_quantity = sum(line.quantity for line in order.lines) or 1
        quantity = max(1, min(quantity, total_quantity))

        if action_key == "stok":
            target_group_key = "kapandi"
            action_label = "Talep stok girişiyle kapandı"
        else:
            target_group_key = "iptal"
            action_label = "Talep iptal edildi"

        target_group = get_request_group_by_key(target_group_key)
        if target_group:
            order.group = target_group

        db.session.flush()

        created_stock_items: list[StockItem] = []
        if action_key == "stok":
            for line in order.lines:
                created_stock_items.append(
                    create_stock_item_from_request_line(
                        order,
                        line,
                        quantity=line.quantity,
                        note=note,
                        actor=actor,
                    )
                )

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
        logs = load_activity_logs()
        return render_template(
            "activity_logs.html",
            active_page="activity_logs",
            logs=logs,
        )

    return app


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
    faulty_count = sum(1 for item in payload if item["status"] == "arizali")
    departments_set: set[str] = {
        item["department"] for item in payload if item.get("department")
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
        "inventory_items": payload,
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

    hardware_type = item.hardware_type.name if item and item.hardware_type else ""
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

    allow_operations = bool(
        item
        and item.hardware_type
        and "yazıcı" in (item.hardware_type.name or "").lower()
    )

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

    return {
        "stock_items": stock_items,
        "stock_logs": [serialize_stock_log(log) for log in logs],
        "stock_categories": categories,
        "stock_status_summary": status_summary,
        "stock_faulty_count": faulty_count,
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
        InfoEntry.query.options(joinedload(InfoEntry.category))
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


def save_information_image(file: FileStorage | None) -> str | None:
    if file is None or not file.filename:
        return None

    filename = secure_filename(file.filename)
    if not filename:
        return None

    extension = Path(filename).suffix
    unique_name = f"{uuid4().hex}{extension}" if extension else uuid4().hex
    upload_dir: Path = current_app.config["INFO_UPLOAD_DIR"]
    target = upload_dir / unique_name
    file.save(target)
    return unique_name


def remove_information_image(filename: str | None) -> None:
    if not filename:
        return

    upload_dir: Path = current_app.config["INFO_UPLOAD_DIR"]
    target = upload_dir / filename
    try:
        target.unlink()
    except FileNotFoundError:
        pass


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
        line_payload = {
            "id": line.id,
            "hardware_type": line.hardware_type,
            "brand": line.brand,
            "model": line.model,
            "quantity": line.quantity,
            "note": line.note,
            "opened_display": opened_display,
        }
        lines_payload.append(line_payload)
        search_tokens.extend(
            [
                line_payload["hardware_type"],
                line_payload["brand"],
                line_payload["model"],
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

    return {"request_groups": request_groups_payload, "hardware_catalog": hardware_catalog}


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
    stock_item.metadata_payload = {
        "factory": item.factory.name if item.factory else "",
        "department": item.department or "",
        "hardware_type": item.hardware_type.name if item.hardware_type else "",
        "brand": item.brand.name if item.brand else "",
        "model": item.model.name if item.model else "",
        "responsible": (
            f"{item.responsible_user.first_name} {item.responsible_user.last_name}"
            if item.responsible_user
            else ""
        ),
    }
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
) -> StockItem:
    title_parts = [line.brand, line.model]
    title = " ".join(part for part in title_parts if part).strip() or line.hardware_type
    stock_item = StockItem(
        source_type="request",
        source_id=order.id,
        reference_code=order.order_no,
        title=title or "Talep Öğesi",
        category="talep",
        quantity=max(1, quantity),
        status="stokta",
        note=note or None,
    )
    stock_item.metadata_payload = {
        "request_no": order.order_no,
        "department": order.department,
        "hardware_type": line.hardware_type,
        "brand": line.brand,
        "model": line.model,
    }
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
    return load_activity_logs(limit)


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
    if User.query.count():
        return

    default_password = generate_password_hash("Parola123!")
    users = [
        User(
            username="m.cetin",
            first_name="Merve",
            last_name="Çetin",
            email="merve.cetin@example.com",
            role="Yönetici",
            department="IT Operasyon",
            password_hash=default_password,
        ),
        User(
            username="a.kaya",
            first_name="Ahmet",
            last_name="Kaya",
            email="ahmet.kaya@example.com",
            role="Satın Alma Uzmanı",
            department="Satın Alma",
            password_hash=default_password,
        ),
        User(
            username="z.ucar",
            first_name="Zeynep",
            last_name="Uçar",
            email="zeynep.ucar@example.com",
            role="Depo Sorumlusu",
            department="Lojistik",
            password_hash=default_password,
        ),
        User(
            username="b.tan",
            first_name="Berk",
            last_name="Tan",
            email="berk.tan@example.com",
            role="Destek Uzmanı",
            department="Teknik Destek",
            password_hash=default_password,
        ),
        User(
            username="e.sonmez",
            first_name="Elif",
            last_name="Sönmez",
            email="elif.sonmez@example.com",
            role="Finans Analisti",
            department="Finans",
            password_hash=default_password,
        ),
    ]
    db.session.add_all(users)
    record_activity(
        area="kullanici",
        action="Varsayılan kullanıcılar eklendi",
        description="Sistem başlangıç kullanıcıları oluşturuldu.",
        metadata={"count": len(users)},
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
