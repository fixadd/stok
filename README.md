# Stok Yönetim Paneli

Bootstrap 5 tabanlı, Flask + PostgreSQL kullanan web tabanlı stok ve IT varlık yönetim panelidir. Uygulama Docker Compose ile 5001 portunda çalışır.

## Kurulum

Önce ortam dosyasını oluşturun:

```bash
cp .env.example .env
```

`.env` içindeki `POSTGRES_PASSWORD` değerini güçlü ve rastgele bir parola ile değiştirin.

Docker Compose'u başlatın:

```bash
docker compose up --build -d
```

Ardından tarayıcıdan `http://localhost:5001` adresine erişebilirsiniz.

## Veritabanı

Uygulama `DATABASE_URL` üzerinden SQLAlchemy bağlantısı kullanır. Compose bu değeri `.env` içindeki PostgreSQL kullanıcı, parola ve veritabanı değerlerinden oluşturur.

PostgreSQL verileri `postgres_data` Docker volume'unda tutulur; web konteynerinin yeniden oluşturulması veritabanını sıfırlamaz.

Üretimde `.env` dosyasını sürüm kontrolüne eklemeyin.

## Veri ve dosya saklama

`./data` klasörü konteynere `/app/data` olarak bağlanır ve bilgi ekranındaki yüklemeler gibi dosya tabanlı verileri korur.

## Yedekleme / Geri Yükleme

Yönetici panelindeki **Veritabanı İşlemleri** bölümünden PostgreSQL `.dump` yedeği dışa aktarılabilir ve geri yüklenebilir. Bu işlemler süper admin yetkisi gerektirir.

## Excel

Stok Excel içe aktarma işlemi yönetici yetkisi ister ve `.xlsx` / `.xlsm` dosyalarını destekler.

## Geliştirme

Geliştirme/test bağımlılıklarını kurmak için:

```bash
pip install -r requirements-dev.txt
```

Yerel geliştirmede `DATABASE_URL` tanımlayıp Flask'ı çalıştırabilirsiniz:

```bash
export DATABASE_URL=postgresql+psycopg://stok:CHANGE_ME@localhost:5432/stok
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

## Test

```bash
pytest -q
```

## Mimari

Route modülleri HTTP katmanında kalır; iş kuralları servis katmanına, ortak sorgular query katmanına, veri dönüşümleri serializer katmanına ve validasyonlar validator katmanına ayrılır. Yeni özellikler mevcut büyük dosyalara eklenmek yerine kendi modüler katmanlarında geliştirilmelidir.

## Temel Modüller

- Envanter Takip
- Lisans Takip
- Bakım Takip
- Stok Takip
- Talep Takip
- Personel Lifecycle
- Bilgi / Dokümantasyon
- Yönetici Paneli
- PostgreSQL yedekleme ve geri yükleme
