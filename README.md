# Baylan IT Varlık ve Stok Yönetim Sistemi

Flask + SQLAlchemy + PostgreSQL tabanlı, Docker Compose ile çalıştırılabilen IT varlık, stok, lisans, bakım, talep, personel yaşam döngüsü ve bilgi yönetim panelidir.

## Ana modüller

- Dashboard / Ana Sayfa
- Envanter Takip
- Lisans Takip
- Stok Takip
- Bakım
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

## Veritabanı

Uygulama PostgreSQL kullanır. PostgreSQL verileri `postgres_data` adlı Docker volume içinde tutulur. Bu nedenle `docker compose down` sonrasında volume silinmediği sürece veritabanı korunur.

Veritabanını silmek için özellikle volume'u da kaldırmanız gerekir:

```bash
docker compose down -v
```

> Bu komut PostgreSQL verilerini siler. Üretim ortamında çalıştırmadan önce mutlaka yedek alın.

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

## Veri yedekleme

PostgreSQL verileri `postgres_data` volume'unda tutulduğu için uygulama container'ını yeniden oluşturmak veriyi tek başına silmez. Üretim ortamında ayrıca düzenli PostgreSQL yedeği alınması önerilir.
