# Veritabanı migration sistemi

Bu klasör, uygulamanın `db.create_all()` ve servis içindeki runtime `CREATE TABLE` yaklaşımından kontrollü migration yapısına geçişi için ayrılmıştır.

## Kural

- Yeni tablo/kolon değişiklikleri uygulama açılışında oluşturulmaz.
- Şema değişiklikleri migration dosyasıyla yapılır.
- Production ortamında migration uygulanmadan yeni uygulama sürümü devreye alınmaz.
- `db.create_all()` mevcut kurulumların devamlılığı için geçiş döneminde korunabilir; yeni şema değişiklikleri için kullanılmamalıdır.

## Sıradaki migration adımları

1. Flask-Migrate/Alembic bağımlılığını ekle.
2. Mevcut PostgreSQL şemasını baseline migration olarak işaretle.
3. `inventory_repairs` tablosunu migration'a taşı.
4. `Repair` SQLAlchemy modelini ekle.
5. Runtime `ensure_table()` çağrılarını kaldır.
6. Migration'ı CI'da boş veritabanında ve mevcut şema üzerinde test et.
7. Production deploy öncesi `flask db upgrade` çalıştır.
