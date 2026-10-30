# Radar: kendi sunucunda PostgreSQL ile çalıştırma

Docker ve Compose bulunan sürekli açık bir Linux
sunucuda API, arayüz, zamanlayıcı, PostgreSQL, yedekleyici ve Proton köprüsü çalışır.
Mevcut makinedeki kurulum da aynıdır; ayrı bir uzak sunucuya otomatik dağıtım yapılmaz.

## Kurulum ve başlatma

Mevcut `.env` dosyasının üzerine yazmayın. Yeni sunucuda `.env.example` dosyasından
başlayıp API/Telegram/SMTP bilgilerini doldurun. Python ortamında `python-dotenv`
bulunmalıdır (projenin `.venv` ortamında hazırdır).

```bash
.venv/bin/python scripts/setup_local_db.py
./scripts/start.sh
```

Kurulum güvenli rastgele PostgreSQL parolası üretir ve `.env` dosyasını yalnızca
kullanıcı okuyabilecek şekilde kaydeder. Önceki uzak bağlantı
`PREVIOUS_DATABASE_URL` içinde korunur. `COMPOSE_FILE` yerel PostgreSQL ek dosyasını
seçer; hydroxide kullanılıyorsa `COMPOSE_PROFILES=proton` etkinleştirilir.
Tekrar çalıştırma verileri veya parolayı sıfırlamaz. Kurulum veri aktarımı yapmaz.

Etkin çalışma ayarları:

```dotenv
AUTO_SCAN_ENABLED=true
SCAN_INTERVAL_MINUTES=60
SCAN_TIMEZONE=Europe/Istanbul
TELEGRAM_ENABLED=true
EMAIL_ENABLED=true
EMAIL_SEND_HOUR=13
```

Web: `http://localhost:3000`. Veritabanı host portu açılmaz. API/arayıüzün mevcut
portları 8008/3000'dır. Uzak sunucuya taşırken yönetim API'si ve ayarlar paneli
kimlik doğrulaması içermediğinden özel ağ/VPN veya kimlik doğrulamalı HTTPS proxy
arkasında tutulmalıdır; bu kurulum kendiliğinden public yayın yapmaz.

Tarama saat başı çalışır. Telegram'a kabul edilen yeni haberler sırayla gönderilir;
uzun taramalarda gönderim tarama bitimini bekler. E-posta 13.00'ten sonraki ilk
döngüde günde bir kez gönderilir. O saatte kapalıysa aynı gün açılışta telafi edilir.
Ayarlar panelinde kaydedilen tarama aralığı `.env` varsayılanının önüne geçer.

## Kalıcılık ve yeniden başlatma

PostgreSQL `postgres-data`, Proton oturumu `hydroxide-auth`, otomatik yedekler
`postgres-backups` Docker volume'lerinde saklanır. `docker compose down` bunları
silmez. **`docker compose down -v` kullanmayın: kalıcı verileri siler.**

Servislerde `restart: unless-stopped` vardır. Docker sistem açılışında etkinse
sunucu yeniden başlatıldığında çalışırlar. Elle durdurulan servisleri
`./scripts/start.sh` ile yeniden başlatın. Sunucuda Docker'ın açılışta çalışması
`systemctl is-enabled docker` ile kontrol edilebilir.

## Yedekleme ve geri yükleme

`db-backup` açılışta ve her 24 saatte bir tutarlı, sıkıştırılmış `pg_dump` yedeği
alır. Başarısızsa beş dakika sonra yeniden dener; yalnızca başarılı yedekten sonra
bir haftadan eski yedekler temizlenir. Yedekler aynı diskte olduğundan disk arızasına
karşı ayrıca başka bir makineye kopyalanmalıdır.

```bash
./scripts/backup.sh                  # backups/ altında dışarı kopyalanabilir dosya
docker compose logs --tail=20 db-backup
```

Geri yükleme kontrolü mevcut veritabanına dokunmadan ayrı bir veritabanında yapılır:

```bash
docker compose exec -T postgres createdb -U radar radar_restore_check
docker compose exec -T postgres pg_restore -U radar -d radar_restore_check --no-owner --no-acl --exit-on-error < backups/YEDEK.dump
docker compose exec -T postgres psql -U radar -d radar_restore_check -c 'SELECT count(*) FROM developments;'
docker compose exec -T postgres dropdb -U radar radar_restore_check
```

Yeni sunucuya geçişte kod, gizli `.env`, veritabanı yedeği ve Proton oturumu gerekir.
Proton oturumunu taşımak yerine yeni sunucuda `scripts/connect_proton.py` ile yeniden
bağlanılabilir. Bu bağlantı komutu e-postayı kapatır; sonrasında `.env` içinde
`EMAIL_ENABLED=true` ve `EMAIL_SEND_HOUR=13` yeniden kontrol edilmelidir.
Eski ve yeni sunucunun zamanlayıcılarını aynı anda çalıştırmayın; ayrı veritabanları
aynı Telegram/e-postayı tekrar gönderebilir.
