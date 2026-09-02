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

Mevcut veritabanında **önce PostgreSQL yedeği alın**. Ardından proje kök dizininden güvenli yardımcı scripti çalıştırın:

```bash
bash scripts/migrate_postgres.sh
```

Script şu işlemleri yapar:

1. PostgreSQL'in hazır olduğunu kontrol eder.
2. Temel `inventory_items` tablosunun bulunduğunu doğrular.
3. `alembic_version` yoksa mevcut şemayı `0001_baseline` olarak işaretler.
4. `alembic upgrade head` çalıştırır.
5. Son migration durumunu gösterir.

Script **`DROP DATABASE`, `DROP TABLE`, `down -v` veya veri silme işlemi yapmaz.**

Elle çalıştırmak gerekirse mevcut kurulum için:

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

> `stamp` komutu tablo oluşturmaz; yalnızca veritabanının mevcut şemasını `0001_baseline` seviyesinde kabul eder.

## Yeni kurulum

Yeni bir veritabanında geçiş dönemindeki `db.create_all()` temel tabloları oluşturduktan sonra migration zinciri uygulanabilir. Uygulama container'ı çalışır durumda olmalıdır.

```bash
bash scripts/migrate_postgres.sh
```

## Kontrol

```bash
alembic current
alembic history
```

Docker ortamında:

```bash
docker compose exec web alembic current
docker compose exec web alembic history
```

Production deploy sırasında hedef revision `head` seviyesine getirilmelidir:

```bash
docker compose exec web alembic upgrade head
```

## Sıradaki adımlar

1. Tamir/bakım modelini migration zincirine bağla.
2. Tamir sorgularını `repair_queries.py` katmanına taşı.
3. Migration'ı CI'da boş veritabanında ve mevcut şema üzerinde test et.
4. Post-repair test/approval, servis belgeleri, fatura ve yedek cihaz alanlarını sonraki migration'larla ekle.
