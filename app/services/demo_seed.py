from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash

from ..models import (
    Brand, Factory, HardwareModel, HardwareType, InfoCategory, InfoEntry,
    InventoryEvent, InventoryItem, InventoryLicense, LdapProfile, LicenseName,
    RequestGroup, RequestLine, RequestOrder, StockCategory, StockItem, StockUnit,
    UsageArea, User, db, find_existing_by_name,
)
from .activity_service import record_activity
from .stock_audit_service import record_stock_log

STOCK_CATEGORY_LABELS = {
    'envanter': 'Envanter',
    'cevre_birimi': 'Çevre Birimi',
    'yazici': 'IP Yazıcı',
    'lisans': 'Lisans',
    'talep': 'Talep',
    'manuel': 'Manuel',
}

def _resolve_stock_category(name: str):
    existing = find_existing_by_name(StockCategory, name)
    if existing:
        return existing
    category = StockCategory(name=name)
    db.session.add(category)
    db.session.flush()
    return category

def _resolve_stock_unit(name: str):
    existing = find_existing_by_name(StockUnit, name)
    if existing:
        return existing
    unit = StockUnit(name=name)
    db.session.add(unit)
    db.session.flush()
    return unit

def seed_initial_data() -> None:
    seed_simple_users()
    seed_product_metadata()
    seed_information_entries()
    seed_inventory_data()
    seed_ldap_profiles()
    seed_request_data()
    seed_stock_reference_data()
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
        if not admin_user.system_role or admin_user.system_role.lower() not in {
            "admin",
            "superadmin",
        }:
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
            for name in [
                "İstanbul Merkez",
                "Ankara Veri Merkezi",
                "İzmir Üretim",
                "Bursa Lojistik",
            ]
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
    users = {f"{user.first_name} {user.last_name}": user for user in User.query.all()}
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

    db.session.add_all(
        [item_primary, item_faulty, printer_central, printer_faulty, item_retired]
    )
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

    total_orders = sum(
        len(group.orders) for group in (open_group, closed_group, cancelled_group)
    )
    record_activity(
        area="talep",
        action="Örnek talepler oluşturuldu",
        description="Açık, kapalı ve iptal statülerine örnek talepler eklendi.",
        metadata={"group_count": 3, "order_count": total_orders},
    )


def seed_stock_reference_data() -> None:
    for category_name in STOCK_CATEGORY_LABELS.keys():
        if not find_existing_by_name(StockCategory, category_name):
            db.session.add(StockCategory(name=category_name))
    for unit_name in ("adet", "kg", "metre"):
        if not find_existing_by_name(StockUnit, unit_name):
            db.session.add(StockUnit(name=unit_name))
    db.session.flush()


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
        category_ref = _resolve_stock_category(sample["category"])
        unit_ref = _resolve_stock_unit("adet")
        stock_item = StockItem(
            source_type="manual",
            title=sample["title"],
            category=sample["category"],
            category_id=category_ref.id if category_ref else None,
            quantity=sample["quantity"],
            unit="adet",
            unit_id=unit_ref.id if unit_ref else None,
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

