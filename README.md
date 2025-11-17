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

## Geliştirme

Yerel geliştirme için Flask uygulamasını doğrudan çalıştırabilirsiniz:

```bash
pip install -r requirements.txt
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

Bu komut arayüzü 5001 portu üzerinden erişilebilir şekilde başlatır.
