# Büyük Dosya Refactor Durumu

Bu belge `main` dalındaki büyük dosyaların güvenli şekilde küçültülmesi için güncel durumu ve kalan işleri gösterir. Refactor adımları küçük ve geri alınabilir tutulur; her kod değişikliği PostgreSQL tabanlı CI ile doğrulanır.

## Tamamlananlar

### 1. Legacy ortak yardımcılar ve demo seed ayrıldı

`app/legacy.py` içindeki aktivite, bakım yardımcıları ve stok audit kayıtları servis katmanına taşındı. Demo/test seed kodu `app/services/demo_seed.py` içine çıkarıldı. `legacy.py` eski import yüzeyini geçici olarak koruyor; production startup seed çalıştırmıyor.

### 2. SQLAlchemy modelleri domain bazlı ayrıldı

`models.py` artık uyumluluk katmanı. Asıl modeller `app/model_domains/` altında:

```text
app/model_domains/
├── base.py
├── users.py
├── inventory.py
├── stock.py
├── maintenance.py
├── requests.py
├── licenses.py
├── information.py
├── catalog.py
├── activity.py
└── common.py
```

`app.models` importları korunuyor ve Alembic tek `db.metadata` üzerinden çalışmaya devam ediyor.

### 3. Büyük template modalları partial'lara çıkarıldı

Envanter, talep, stok, admin, lisans ve bakım template'lerindeki modal blokları ilgili `*_partials/` klasörlerine ayrıldı. Jinja context'i include üzerinden korunuyor.

### 4. Sayfa JavaScript'i ayrıştırılmaya başlandı

Güvenli şekilde taşınabilen inline script'ler `app/static/js/pages/` altına çıkarıldı. Jinja'ya doğrudan bağlı scriptler zorla taşınmadı.

### 5. UI teması

Yeni minimal/Vercel-benzeri görünüm `redesign.css` ile aktif. `tabler-overrides.css` yalnızca uyumluluk kurallarını içeriyor. Bilgi ekranı da aynı tasarım diline getirildi.

### 6. Yapılandırılabilir ayarlar ve özel alan altyapısı

Seçilebilir değerler için PostgreSQL tabanlı ayar listeleri ve seçenekleri, admin için hızlı `+`/dişli yönetimi, özel alanlar, alan grupları ve dashboard widget metadata'sı eklendi. Envanter özel alanları oluşturma/düzenleme akışına bağlandı; mevcut özel değerler düzenleme modalı açılırken yükleniyor. İsteğe bağlı özel alanlar boş bırakılabilir ve kısmi güncellemeler gönderilmediği alanları değiştirmiyor.

### 7. Platform genişletme altyapısı

Koşullu alan kuralları, bağımlı lookup'lar, rapor tanımları, bildirim kuralları ve API token metadata'sı için PostgreSQL/Alembic altyapısı eklendi. Ayar seçenekleri aktif/pasif tutulabiliyor; hard-delete yerine deaktivasyon yaklaşımı korunuyor.

### 8. Migration ve CI doğrulaması

Yeni migration'lar PostgreSQL 17 üzerinde temiz veritabanında doğrulandı. Seed kayıtları Python/ORM varsayılanlarına bağımlı olmayacak şekilde gerekli `active`, timestamp ve JSON değerlerini açıkça veriyor. Testler güncel migration head'i ve yeni yapılandırma tablolarını kontrol ediyor.

### 9. Entegrasyon kontrolü

App factory ile singleton uygulamanın extension route'ları aynı davranışa getirildi. Testler PostgreSQL şemasıyla çalışıyor; smoke test verileri mevcut demo kayıtlarına bağımlı olmayacak şekilde izole edildi. Geçici CI teşhis workflow'ları kaldırıldı.

## Kalan büyük işler

### `app/legacy.py`

Hâlâ ana monolit. Kalan route/business/payload fonksiyonları konu bazında mevcut servis ve query modüllerine taşınacak. Hedef, yeni kodun legacy'ye girmemesi ve sonunda dosyanın kaldırılmasıdır.

### Büyük template'ler

Modal ayrımı yapıldı; sıradaki güvenli adım liste/filtre/table/summary parçalarını Jinja include'larına ayırmak. Inline JavaScript yalnızca Jinja bağımlılığı olmayan bloklarda taşınacak.

### `app/static/css/style.css`

Eski global UI kuralları ile yeni tema örtüşüyor. Kullanım denetimi yapıldıktan sonra `base.css`, `components.css`, sayfa CSS'leri ve gerekirse `legacy.css` olarak ayrılacak; en son `style.css` kaldırılacak.

### `app/static/js/pages/license_tracking-1.js`

Dosya büyüklüğü nedeniyle fonksiyon sorumluluklarına göre incelenecek; sırf satır sayısını düşürmek için mekanik bölme yapılmayacak.

### `app/personnel_lifecycle.py` / `app/services/repair_service.py`

Orta öncelikli. Fonksiyon grupları netleştirilerek servis/query sorumluluklarına göre bölünecek.

## Korumalı kurallar

- Yalnızca PostgreSQL kullanılacak.
- Runtime içinde `create_all()` / `drop_all()` olmayacak.
- Seed/demo kodu production startup yolunda çalışmayacak.
- Route katmanı SQL ve iş kuralı deposu olmayacak.
- Alembic schema sahibi olmaya devam edecek.
- `.before-*`, `.bak`, `~` ve üretilmiş audit dosyaları repository'ye alınmayacak.
