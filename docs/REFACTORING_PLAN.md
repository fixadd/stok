# Büyük Dosya Refactor Planı

Bu belge, mevcut `main` dalındaki büyük dosyaları güvenli şekilde küçültmek için hedef mimariyi tanımlar. Amaç tek seferde büyük dosya yeniden yazmak değil; her modülü çalışır halde tutarak küçük ve geri alınabilir değişikliklerle parçalamaktır.

## Öncelik sırası

1. `app/legacy.py` — 213 KB: ilk ve en kritik aday.
2. `app/templates/inventory_tracking.html` — 104 KB.
3. `app/templates/talep_takip.html` — 84 KB.
4. `app/templates/stock_tracking.html` — 69 KB.
5. `app/templates/admin_panel.html` — 64 KB.
6. `app/templates/license_tracking.html` — 55 KB.
7. `app/static/css/style.css` — 42 KB; yeni Vercel-benzeri tema ile büyük ölçüde örtüşüyor.
8. `app/models.py` — 28 KB.
9. `app/templates/maintenance_tracking.html` — 20 KB.
10. `app/templates/admin_panel_modals.html` — 18 KB.
11. `app/personnel_lifecycle.py` — 16 KB.
12. `app/services/repair_service.py` — 16 KB.

## 1. `app/legacy.py`

Hedef: production route/business kodunun legacy dosyasından tamamen çıkarılması ve dosyanın sonunda silinmesi.

Önerilen ayrım:

- `app/seed/demo_data.py` — yalnızca test/demo seed fonksiyonları.
- `app/services/inventory_service.py` — envanter iş kuralları.
- `app/services/stock_service.py` — stok iş kuralları.
- `app/services/maintenance_service.py` — bakım/onarım iş kuralları.
- `app/services/request_service.py` — talep iş kuralları.
- `app/services/activity_service.py` — aktivite/audit kayıtları.
- `app/queries/*` — salt okuma sorguları.
- `app/routes/*` — HTTP request/response katmanı.

Kalan legacy fonksiyonları konu bazında taşındıktan sonra `legacy.py` yalnızca geçici uyumluluk katmanı olarak tutulmalı; yeni kod buraya eklenmemeli.

## 2. `inventory_tracking.html`

Önerilen yapı:

```text
app/templates/inventory/
├── list.html
├── detail.html
├── partials/
│   ├── filters.html
│   ├── table.html
│   ├── summary.html
│   └── empty_state.html
└── modals/
    ├── assignment.html
    ├── maintenance.html
    └── transfer.html
```

Sayfadaki inline JavaScript ayrı JS modüllerine taşınmalı.

## 3. `talep_takip.html`

Önerilen yapı:

```text
app/templates/requests/
├── list.html
├── detail.html
├── partials/
│   ├── filters.html
│   ├── table.html
│   └── status_badge.html
└── modals/
    ├── create.html
    ├── edit.html
    └── status.html
```

Talep sorguları `request_queries.py` / `request_query_service.py`, iş kuralları `request_service.py` içinde kalmalı.

## 4. `stock_tracking.html`

Önerilen yapı:

```text
app/templates/stock/
├── list.html
├── detail.html
├── partials/
│   ├── filters.html
│   ├── table.html
│   └── summary.html
└── modals/
    ├── movement.html
    ├── edit.html
    └── delete.html
```

Mevcut `stock.py` route'ları ince tutulacak; veri hazırlama `stock_service.py` ve `stock_query_service.py` üzerinden yapılacak.

## 5. `admin_panel.html`

`admin_panel_modals.html` zaten ayrı olduğu için ikinci aşamada paneli domain bazlı partial'lara ayırmak yeterli:

```text
app/templates/admin/
├── dashboard.html
├── users.html
├── catalog.html
├── stock_metadata.html
└── partials/
    ├── user_table.html
    ├── catalog_table.html
    └── stats.html
```

## 6. `license_tracking.html`

Önerilen yapı:

```text
app/templates/license/
├── list.html
├── detail.html
├── partials/
│   ├── filters.html
│   ├── table.html
│   └── counters.html
└── modals/
    ├── create.html
    └── edit.html
```

## 7. `style.css`

Mevcut 42 KB dosyada eski UI sistemi ile yeni minimal tema üst üste bulunuyor. Önce yeni `redesign.css` ile gerçekten kullanılan stiller doğrulanmalı. Ardından:

- global reset → `base.css`
- ortak form/button/table → `components.css`
- dashboard → `pages/dashboard.css`
- inventory/stock/license → ilgili sayfa CSS'leri
- yalnızca gerçekten kullanılan legacy kurallar → `legacy.css`

Son aşamada `style.css` tamamen kaldırılmalı. `redesign.css` tek başına nihai tema dosyası olmak yerine bu modüler yapının parçaları haline getirilebilir.

## 8. `models.py`

Model sınıfları domain bazlı ayrılmalı:

```text
app/models/
├── __init__.py
├── base.py
├── users.py
├── inventory.py
├── stock.py
├── maintenance.py
├── requests.py
├── licenses.py
├── information.py
└── activity.py
```

`db` ve ortak model yardımcıları `base.py` içinde tutulmalı. Alembic `target_metadata` tek bir `db.metadata` üzerinden çalışmaya devam etmeli.

## 9. `maintenance_tracking.html`

`inventory` ve `maintenance` ilişkisi nedeniyle bakım ekranı şu parçalara ayrılmalı:

- liste/filtreler
- bakım özeti
- bakım kayıt tablosu
- kayıt/düzenleme modalı
- detay görünümü

## 10. `personnel_lifecycle.py` ve `repair_service.py`

Bu dosyalar orta öncelikli. Önce fonksiyon grupları çıkarılmalı, sonra tek sorumluluklu servis/query modüllerine taşınmalı. Sadece dosya boyunu düşürmek için bölme yapılmamalı.

## Güvenlik ve çalışma kuralı

- PostgreSQL dışına çıkılmayacak.
- Runtime içinde `create_all()` / `drop_all()` olmayacak.
- Seed/demo kodu production startup yolunda çalışmayacak.
- Route katmanı SQL ve iş kuralı deposu olmayacak.
- Büyük dosyalar taşınırken her adım CI ile doğrulanacak.
- `.before-*`, `.bak`, `~` ve üretilmiş audit dosyaları repository'ye alınmayacak.
