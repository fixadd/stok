# Baylan IT Varlık ve Stok Yönetim Sistemi

Flask + SQLAlchemy + PostgreSQL tabanlı, Docker Compose ile çalıştırılabilen IT varlık, stok, lisans, bakım, talep, personel yaşam döngüsü ve bilgi yönetim panelidir.

## Ana modüller

- Dashboard / Ana Sayfa
- Envanter Takip
- Lisans Takip
- Stok Takip
- Tamir / Bakım Takibi
- Hurdalar
- Talep Takip
- Personel Lifecycle
- Bilgiler / bilgi bankası
- Profil ve kullanıcı yetkilendirme
- Yönetici kayıtları / Activity Log

## Teknoloji

- Python 3.11
- Flask
- Flask-SQLAlchemy / SQLAlchemy
- PostgreSQL 17
- Psycopg
- Alembic migration altyapısı
- Merkezi config ve hata yönetimi
- Güvenlik response header'ları
- Docker / Docker Compose
- Bootstrap tabanlı web arayüzü

## Docker ile kurulum

1. Ortam dosyasını oluşturun:

```bash
cp .env.example .env
```

2. `.env` içindeki `POSTGRES_PASSWORD` değerini güçlü ve benzersiz bir parola ile değiştirin.

3. Uygulamayı başlatın:

```bash
docker compose up -d --build
```

4. Durumu kontrol edin:

```bash
docker compose ps
docker compose logs -f web
```

5. Paneli açın:

```text
http://localhost:5001
```

## Veritabanı ve migration

PostgreSQL verileri `postgres_data` adlı Docker volume içinde tutulur. `docker compose down` volume'u silmediği için normal container yeniden oluşturma işlemleri veriyi silmez.

Şema değişiklikleri için `migrations/versions` altındaki Alembic migration'ları kullanın. Üretim veritabanında migration çalıştırmadan önce yedek alın:

```bash
bash scripts/backup_postgres.sh
```

Docker ortamında migration çalıştırmak için:

```bash
docker compose exec web python -m alembic upgrade head
```

Mevcut migration durumunu görmek için:

```bash
docker compose exec web python -m alembic current
docker compose exec web python -m alembic heads
```

> Uygulama halen geçiş döneminde `db.create_all()` çağrısını da içerir. Yeni şema değişikliklerini yalnızca `db.create_all()` ile çözmeye çalışmayın; kalıcı schema değişiklikleri migration olarak eklenmelidir.

Veritabanını silmek için özellikle volume'u da kaldırmanız gerekir:

```bash
docker compose down -v
```

> **DİKKAT:** Bu komut PostgreSQL verilerini siler. Üretim ortamında çalıştırmayın; yalnızca verinin bilinçli olarak silinmesi gereken durumlarda kullanın.

## Güvenli güncelleme / deploy akışı

Üretim sunucusunda önerilen sıra:

```bash
git pull --ff-only origin main
bash scripts/backup_postgres.sh
docker compose up -d --build
docker compose exec web python -m alembic upgrade head
docker compose ps
```

Önceki sürüme dönmek gerektiğinde önce yedek alın ve migration geri alma kararını doğrulayın. Uygulama container'ını yeniden oluşturmak için `docker compose down` kullanılabilir; **`down -v` kullanılmamalıdır**.

## Geliştirme

Docker dışında çalıştırmak için Python 3.11 ve gerekli bağımlılıkları kurup `DATABASE_URL` ortam değişkenini PostgreSQL bağlantı adresine ayarlayın:

```bash
pip install -r requirements.txt
flask --app app run --host 0.0.0.0 --port 5001 --debug
```

## Güvenlik notları

- Gerçek parolaları Git'e göndermeyin.
- `.env` dosyası `.gitignore` tarafından hariç tutulur.
- `.env.example` yalnızca örnek yapılandırmadır; gerçek parola içermez.
- Varsayılan/örnek yönetici parolasını üretim ortamında kullanmayın.
- Üretim ortamında güçlü ve benzersiz PostgreSQL parolası kullanın.

## Veri yedekleme ve geri yükleme

PostgreSQL verileri `postgres_data` volume'unda tutulduğu için uygulama container'ını yeniden oluşturmak veriyi tek başına silmez. Bunun yanında düzenli mantıksal yedek alınması önerilir.

Yedek almak:

```bash
bash scripts/backup_postgres.sh
```

Varsayılan saklama süresi 7 gündür. Örneğin 30 günlük saklama için:

```bash
bash scripts/backup_postgres.sh 30
```

Geri yüklemek:

```bash
bash scripts/restore_postgres.sh backups/postgres/stok_YYYYMMDD_HHMMSS.dump
```

Geri yükleme mevcut veritabanındaki nesneleri temizleyip yedeği geri getirir ve işlem öncesinde açık onay ister.

> Üretim ortamında `docker compose down -v` çalıştırmadan ve geri yükleme yapmadan önce mutlaka doğrulanabilir bir yedek bulunduğundan emin olun.
