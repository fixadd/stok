# Stok Uygulaması Mimari Kuralları

Bu proje büyüdükçe yeni özellik eklemeyi kolaylaştırmak ve tek bir dosyanın aşırı büyümesini önlemek için aşağıdaki yapı izlenir.

## Katmanlar

```text
app/
├── __init__.py          # Uygulama kurulumu, extension ve route registration
├── models.py             # Mevcut veri modelleri; ilerleyen aşamalarda domain dosyalarına ayrılabilir
├── routes/               # HTTP/Flask katmanı
├── services/             # İş kuralları, transaction ve domain workflow'ları
├── queries/              # Tekrar kullanılan database sorguları
├── utils/                # Küçük ve bağımsız yardımcılar
├── templates/            # Sayfa ve modal şablonları
└── static/               # CSS ve JavaScript
```

## Route kuralları

Route fonksiyonları mümkün olduğunca şu işleri yapar:

1. Request'i almak.
2. Temel HTTP/gövde kontrolünü yapmak.
3. Yetki kontrolünü yapmak.
4. Service fonksiyonunu çağırmak.
5. HTTP response üretmek.

Database değişiklikleri, domain kuralları ve transaction akışları route dosyasına taşınmaz.

Örnek:

```python
@bp.post('/api/inventory')
def create_inventory():
    data = request.get_json(silent=True) or {}
    result, status = inventory_service.create_inventory(deps, data)
    return jsonify(result), status
```

## Service kuralları

Service fonksiyonları iş akışının sahibidir. Örneğin:

- envanter oluşturma/güncelleme
- zimmet verme/iade
- lisans atama/pasife alma
- stok giriş/çıkış
- bakım kaydı oluşturma

Service'ler tekrar kullanılabilir ve mümkün olduğunca açık dependency/data parametreleriyle çalışır.

## Query kuralları

Aynı sorgu birden fazla yerde gerekiyorsa `queries/` altına taşınır. Route ve template içinde tekrar eden karmaşık ORM sorguları bırakılmaz.

## Response kuralları

API cevapları aynı başarı/hata formatını kullanmalıdır. Ortak response yardımcıları zaman içinde `utils/responses.py` altında merkezileştirilecektir.

## Validation kuralları

Validation domain'e göre ayrılır:

```text
validators/
├── inventory.py
├── license.py
├── stock.py
└── request.py
```

Frontend validation kullanıcı deneyimi içindir; backend validation her zaman zorunludur.

## Authorization kuralları

Yetki yalnızca UI'da gizleme ile sağlanmaz. Veri değiştiren endpoint'ler backend tarafında da rol kontrolü yapar.

Rol seviyesi:

```text
user < admin < superadmin
```

## Yeni özellik ekleme standardı

Yeni bir özellik mümkün olduğunca şu sırayla eklenir:

```text
model
  ↓
query
  ↓
service
  ↓
validator
  ↓
route
  ↓
serializer
  ↓
template / JS
  ↓
test
```

Bir özelliği yalnızca çalıştırmak için `app/__init__.py` içine büyük miktarda business logic eklenmez.

## Büyük dosya sınırı

Yeni kod eklerken mevcut dosya büyüklüğü mutlaka gözden geçirilir. Bir dosya farklı sorumlulukları toplamaya başladıysa önce parçalanır.

Amaç tek seferde çok sayıda mikro dosya üretmek değil; sorumlulukları net ve tekrar kullanılabilir orta boy modüllere ayırmaktır.

## Mevcut durum

İlk servis ayrıştırmaları:

- `services/inventory_service.py`
- `services/assignment_service.py`
- `services/stock_service.py`
- `services/license_service.py`

Route katmanında bunların HTTP wrapper'ları kullanılır.

Bir sonraki mimari aşamada `app/__init__.py` içindeki dashboard, migration, serialization ve tekrar kullanılan query/business helper'ları aynı prensiple dışarı taşınacaktır.
