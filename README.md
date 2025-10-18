# Stok Yönetim Paneli

Bootstrap 5 tasarımına sahip, Docker ile 5001 portunda ayağa kaldırılabilen basit bir stok yönetim arayüzü.

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

Compose ortamı ilk kez ayağa kaldırıldığında `stok-db` adlı volume oluşturulur ve veritabanı dosyası konteyner içindeki `/data/stok.db` konumunda saklanır. Böylece konteyner yeniden başlatıldığında veya güncellendiğinde veriler korunmaya devam eder.

## Geliştirme

Yerel geliştirme için Flask uygulamasını doğrudan çalıştırabilirsiniz:

```bash
pip install -r requirements.txt
python -m flask --app app run --host 0.0.0.0 --port 5001 --debug
```

Bu komut arayüzü 5001 portu üzerinden erişilebilir şekilde başlatır.
