# Stok Yönetim Paneli

Bootstrap 5 tabanlı, Flask + PostgreSQL kullanan web tabanlı stok ve IT varlık yönetim panelidir. Uygulama Docker Compose ile 5001 portunda çalışır.

## Varsayılan Yönetici Hesabı

Uygulama ilk kez başlatıldığında varsayılan yönetici hesabı oluşturulur:

| Kullanıcı Adı | Şifre |
| ------------- | ----- |
| `admin`       | `admin` |

İlk girişte bu hesap için yeni ve güçlü bir şifre belirlemeniz istenir.

## Kurulum

Önce ortam dosyasını oluşturun:

```bash
cp .env.example .env
```

Windows'ta `.env.example` dosyasını `.env` adıyla kopyalayabilirsiniz. Ardından `POSTGRES_PASSWORD` değerini güçlü ve rastgele bir parola ile değiştirin.

Docker Compose'u başlatın:

```bash
docker compose up --build -d
```

Ardından tarayıcıdan `http://localhost:5001` adresine erişebilirsiniz.

Compose yapısında uygulama ve PostgreSQL ayrı servisler olarak çalışır. PostgreSQL verileri `postgres_data` isimli Docker volume'unda tutulur; web konteynerinin yeniden oluşturulması veritabanını sıfırlamaz.

## Veritabanı

Uygulama `DATABASE_URL` üzerinden SQLAlchemy bağlantısı kullanır. Compose bu değeri `.env` içindeki PostgreSQL kullanıcı, parola ve veritabanı değerlerinden oluşturur.

Üretimde PostgreSQL parolasını kesinlikle gerçek bir gizli değerle değiştirin ve `.env` dosyasını sürüm kontrolüne eklemeyin.

## Veri ve dosya saklama

`./data` klasörü konteynere `/app/data` olarak bağlanır ve bilgi ekranındaki yüklemeler gibi dosya tabanlı verileri korur. PostgreSQL verileri ise `postgres_data` volume'unda tutulur.

## Yedekleme / Geri Yükleme

Yönetici panelindeki **Veritabanı İşlemleri** bölümünden PostgreSQL `.dump` yedeği dışa aktarılabilir ve geri yüklenebilir. Bu işlemler yalnızca süper admin yetkisine açıktır.

## Excel

Stok Excel içe aktarma işlemi yönetici yetkisi ister ve `.xlsx` / `.xlsm` dosyalarını destekler.

## Geliştirme

Yerel geliştirme için Python ortamını kurup `DATABASE_URL` tanımlamanız gerekir. Örnek:

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://stok:CHANGE_ME@localhost:5432/stok
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg://stok:CHANGE_ME@localhost:5432/stok"
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

## Test

Smoke testleri çalıştırmak için:

```bash
pytest -q
```

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
