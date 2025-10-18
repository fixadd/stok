from __future__ import annotations

from datetime import datetime, timedelta

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from .models import (
    Brand,
    Factory,
    HardwareModel,
    HardwareType,
    InfoCategory,
    InventoryEvent,
    InventoryItem,
    InventoryLicense,
    LdapProfile,
    LicenseName,
    RequestGroup,
    RequestLine,
    RequestOrder,
    UsageArea,
    User,
    db,
    find_existing_by_name,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="stok-admin-secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///stok.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_initial_data()

    @app.route("/")
    def index():
        return render_template("index.html", active_page="index")

    @app.route("/envanter-takip")
    def inventory_tracking():
        payload = load_inventory_payload()
        return render_template(
            "inventory_tracking.html",
            active_page="inventory_tracking",
            **payload,
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
        db.session.commit()

        flash("Yeni kullanıcı başarıyla oluşturuldu.", "success")
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

    @app.route("/talep-takip")
    def talep_takip():
        request_groups = []
        for group in RequestGroup.query.order_by(RequestGroup.id).all():
            orders_payload = []
            for order in group.orders:
                opened_display = order.opened_at.strftime("%d.%m.%Y %H:%M")
                lines_payload = [
                    {
                        "hardware_type": line.hardware_type,
                        "brand": line.brand,
                        "model": line.model,
                        "quantity": line.quantity,
                        "note": line.note,
                    }
                    for line in order.lines
                ]

                search_tokens = [
                    order.order_no,
                    order.requested_by,
                    order.department,
                    opened_display,
                ]
                for line in lines_payload:
                    search_tokens.extend(
                        [
                            line.get("hardware_type"),
                            line.get("brand"),
                            line.get("model"),
                            line.get("note"),
                        ]
                    )

                orders_payload.append(
                    {
                        "order_no": order.order_no,
                        "requested_by": order.requested_by,
                        "department": order.department,
                        "opened_display": opened_display,
                        "lines": lines_payload,
                        "item_count": len(lines_payload),
                        "total_quantity": sum(line["quantity"] for line in lines_payload),
                        "search_index": " ".join(token for token in search_tokens if token).lower(),
                    }
                )

            request_groups.append(
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

        return render_template(
            "talep_takip.html",
            active_page="talep_takip",
            request_groups=request_groups,
            hardware_catalog=hardware_catalog,
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

    payload = []
    faulty_count = 0
    departments_set: set[str] = set()

    for item in items:
        responsible = (
            f"{item.responsible_user.first_name} {item.responsible_user.last_name}"
            if item.responsible_user
            else "Henüz atanmamış"
        )
        brand_name = item.brand.name if item.brand else ""
        model_name = item.model.name if item.model else ""
        status_value = (item.status or "aktif").lower()

        if status_value == "arizali":
            faulty_count += 1

        if item.department:
            departments_set.add(item.department)

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

        licenses = [
            {
                "id": license.id,
                "name": license.name,
                "status": license.status,
            }
            for license in item.licenses
        ]

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

        payload.append(
            {
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
                "note": item.note,
                "status": status_value,
                "history": history,
                "licenses": licenses,
                "search_index": " ".join(filter(None, search_tokens)).lower(),
            }
        )

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

    return {
        "users": users,
        "product_options": product_options,
        "brand_models": brand_models,
        "ldap_profiles": ldap_profiles,
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
    seed_inventory_data()
    seed_ldap_profiles()
    seed_request_data()
    db.session.commit()


def seed_simple_users() -> None:
    if User.query.count():
        return

    users = [
        User(
            username="m.cetin",
            first_name="Merve",
            last_name="Çetin",
            email="merve.cetin@example.com",
            role="Yönetici",
            department="IT Operasyon",
        ),
        User(
            username="a.kaya",
            first_name="Ahmet",
            last_name="Kaya",
            email="ahmet.kaya@example.com",
            role="Satın Alma Uzmanı",
            department="Satın Alma",
        ),
        User(
            username="z.ucar",
            first_name="Zeynep",
            last_name="Uçar",
            email="zeynep.ucar@example.com",
            role="Depo Sorumlusu",
            department="Lojistik",
        ),
        User(
            username="b.tan",
            first_name="Berk",
            last_name="Tan",
            email="berk.tan@example.com",
            role="Destek Uzmanı",
            department="Teknik Destek",
        ),
        User(
            username="e.sonmez",
            first_name="Elif",
            last_name="Sönmez",
            email="elif.sonmez@example.com",
            role="Finans Analisti",
            department="Finans",
        ),
    ]
    db.session.add_all(users)


def seed_product_metadata() -> None:
    if not UsageArea.query.count():
        db.session.add_all(
            UsageArea(name=name)
            for name in ["Ofis", "Saha", "Veri Merkezi", "Üretim", "Uzaktan Çalışma"]
        )

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

    if not InfoCategory.query.count():
        db.session.add_all(
            InfoCategory(name=name)
            for name in ["Güvenlik", "İş Uygulamaları", "İletişim", "Altyapı"]
        )

    if not Factory.query.count():
        db.session.add_all(
            Factory(name=name)
            for name in ["İstanbul Merkez", "Ankara Veri Merkezi", "İzmir Üretim", "Bursa Lojistik"]
        )

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
        related_machine_no="",
        machine_no="PRN-FIN-02",
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

    db.session.add_all([item_primary, item_faulty, item_retired])


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


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
