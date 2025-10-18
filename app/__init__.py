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

from .models import (
    Brand,
    Factory,
    HardwareModel,
    HardwareType,
    InfoCategory,
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
