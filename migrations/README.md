# Veritabanı migration sistemi

Bu klasör, uygulamanın `db.create_all()` ve servis içindeki runtime `CREATE TABLE` yaklaşımından kontrollü migration yapısına geçişi için kullanılır.

## Kural

- Yeni tablo/kolon değişiklikleri uygulama açılışında oluşturulmaz.
- Şema değişiklikleri migration dosyasıyla yapılır.
- Production ortamında migration uygulanmadan yeni uygulama sürümü devreye alınmaz.
- `db.create_all()` mevcut kurulumların devamlılığı için geçiş döneminde korunabilir; yeni şema değişiklikleri için kullanılmamalıdır.

## Mevcut migration zinciri

- `0001_baseline`: mevcut PostgreSQL şemasını migration geçmişinin başlangıcı olarak işaretler; veri veya tablo silmez.
- `0002_inventory_repairs`: `inventory_repairs` tablosunu ve sorgu performansı için gerekli indeksleri tanımlar.

`0002` migration'ı `CREATE TABLE IF NOT EXISTS` kullandığı için mevcut kurulumlarda daha önce runtime tarafından oluşturulmuş `inventory_repairs` tablosunu yeniden oluşturmaz.

## Mevcut sunucuyu migration sistemine alma

Mevcut veritabanı zaten çalışıyorsa önce bir PostgreSQL yedeği alın. Ardından migration geçmişini mevcut şemaya eşitleyin:

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

> `stamp` komutu tablo oluşturmaz; yalnızca veritabanının mevcut şemasını `0001_baseline` seviyesinde kabul eder.

## Yeni kurulum

Yeni bir veritabanında geçiş dönemindeki `db.create_all()` temel tabloları oluşturduktan sonra migration zinciri uygulanabilir.

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

## Kontrol

```bash
alembic current
alembic history
```

Production deploy sırasında hedef revision `head` seviyesine getirilmelidir:

```bash
alembic upgrade head
```

## Sıradaki adımlar

1. `InventoryRepair` SQLAlchemy modelini ekle.
2. `repair_service.py` içindeki runtime `ensure_table()` çağrılarını kaldır.
3. Tamir sorgularını `repair_queries.py` katmanına taşı.
4. Migration'ı CI'da boş veritabanında ve mevcut şema üzerinde test et.
5. Post-repair test/approval, servis belgeleri, fatura ve yedek cihaz alanlarını sonraki migration'larla ekle.
