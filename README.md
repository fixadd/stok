# Stok Yönetim Paneli

Bootstrap 5 tasarımına sahip, Docker ile 5001 portunda ayağa kaldırılabilen basit bir stok yönetim arayüzü.

## Varsayılan Yönetici Hesabı

Uygulama ilk kez başlatıldığında sisteme giriş yapabilmek için varsayılan olarak şu yönetici hesabı oluşturulur:

| Kullanıcı Adı | Şifre |
| ------------- | ----- |
| `admin`       | `admin` |

İlk girişte bu hesap için yeni ve güçlü bir şifre belirlemeniz istenir. Şifre değişikliğini tamamladıktan sonra panelin tüm özelliklerine erişebilirsiniz.

## Kurulum

Projeyi yerel ortamınızda çalıştırmak için Docker kullanabilirsiniz:

```bash
docker build -t stok-uygulama .
docker run --rm -p 5001:5001 stok-uygulama
```

Ardından tarayıcınızdan `http://localhost:5001` adresine gidin.

Docker Compose tercih ediyorsanız aşağıdaki komutu kullanabilirsiniz:

```bash
docker compose up --build
```

Compose ortamı ilk kez ayağa kaldırıldığında proje kök dizininde `data/` klasörü oluşturulur ve uygulama bu klasörün içine `stok.db` dosyası ile yüklenen görsellere ait alt klasörleri kaydeder. Docker konteyneri çalışırken bu klasör `/app/data` olarak bağlanır; böylece konteyner yeniden başlatıldığında veya güncellendiğinde veriler korunur. `data/` klasörünü başka bir ortama taşıyarak veya versiyon kontrolü dışında bir yedekle saklayarak veritabanını koruyabilirsiniz.


## Veritabanı Konumu

Varsayılan çalışmada uygulama veritabanını proje kökündeki `./data/stok.db` dosyasında tutar. `DATA_DIR` değişkeni verilirse aynı varsayılan isimle bu klasörün altında `stok.db` oluşturulur.

Harici bir yedek disk veya özel bir dosya yolu kullanmak için `DATABASE_PATH` ortam değişkenini doğrudan veritabanı dosyasına işaret edecek şekilde verebilirsiniz:

```bash
DATABASE_PATH=/mnt/backup/stok/stok.db docker compose up --build
```

Bu kullanımda uygulama `/mnt/backup/stok/` klasörünü otomatik oluşturur; yüklenen dosyalar ve diğer varsayılan veri klasörleri için `DATA_DIR` kullanılmaya devam eder.

## Geliştirme

Yerel geliştirme için Flask uygulamasını doğrudan çalıştırabilirsiniz:

```bash
pip install -r requirements.txt
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

Bu komut arayüzü 5001 portu üzerinden erişilebilir şekilde başlatır.
