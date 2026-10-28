# Radar günlük özeti — Proton / hydroxide

Günlük saat: **16:00 Europe/Istanbul**. Önizleme gönderim yapmadan hazırlanabilir. Hesap bağlantısı tamamlanmadan `EMAIL_ENABLED` kapalı kalmalıdır.

## Hazır kurulum

Hydroxide'ın [GitHub deposu](https://github.com/emersion/hydroxide) [Codeberg'e taşındı](https://codeberg.org/emersion/hydroxide). Yerel imaj resmî Codeberg `02b3b6c8aff726d2404b6ed5f6ba1b7937e1f30e` revizyonundan derlenir. `proton` Compose profili SMTP köprüsünü açar; hosta SMTP portu yayınlanmaz. Hesap oturumu `hydroxide-auth` volume'ünde saklanır. Bu volume ve köprü parolası korunmalıdır.

```bash
docker compose --profile proton build hydroxide
docker compose --profile proton up -d hydroxide
```

## Hesabı bağlama — kullanıcının terminalinde

Tek komutla giriş yapıp yalnızca bir deneme özeti göndermek için, proje klasöründeki yardımcıyı kendi terminalinizde çalıştırabilirsiniz:

```bash
python3 scripts/connect_proton.py --account your-address@proton.me --recipient recipient@example.com --send-test
```

Proton giriş parolası hydroxide'ın etkileşimli alanına girilir. Başarılı giriş sonunda verilen `Bridge password`, yardımcının sonraki gizli alanına yapıştırılır. Yardımcı SMTP bağlantısını doğrular ve köprü parolasını `.env` içine korumalı olarak kaydeder; Proton giriş parolasını kendisi kaydetmez. `--send-test` yalnızca o deneme işlemi için maili açar, kalıcı günlük gönderim kapalı kalır. Gönderim yalnızca komutta belirtilen alıcıya yapılır. Alıcı belirtilmezse gönderen hesabına deneme yapılır. Aşağıdaki adımlar aynı bağlantının elle kurulumudur.

Proton parolanızı sohbet mesajına veya `.env` dosyasına yazmayın. Aşağıdaki oturum açma komutunu kendi terminalinizde çalıştırın; Proton parolası, gerekiyorsa ikinci parola/2FA/insan doğrulama adımı orada istenir.

```bash
docker compose stop hydroxide
docker compose --profile proton run --rm hydroxide auth your-address@proton.me
```

Başarılı girişten sonra verilen **bridge password** Radar'ın SMTP parolasıdır. Proton giriş parolası değildir. Bu değeri yerelde `.env` içine kaydedin:

```dotenv
EMAIL_ENABLED=true
EMAIL_SMTP_HOST=hydroxide
EMAIL_SMTP_PORT=1025
EMAIL_SMTP_SECURITY=local
EMAIL_SMTP_USER=your-address@proton.me
EMAIL_SMTP_PASSWORD="generated-bridge-password"
EMAIL_FROM=your-address@proton.me
EMAIL_RECIPIENTS=recipient@example.com
EMAIL_SEND_HOUR=16
SCAN_TIMEZONE=Europe/Istanbul
# Yayına alınmış site adresi varsa ekleyin; yerel bağlantı göndermeyin.
EMAIL_PUBLIC_URL=
```

`EMAIL_FROM`, Proton hesabınıza tanımlı gönderen adresi olmalıdır. Birden fazla alıcı virgülle ayrılır. `local` modu yalnızca loopback adreslerini veya Compose içindeki `hydroxide` servisini kabul eder. Başka bir sunucuda normal SMTP kullanırken `starttls` ya da `ssl` seçilir; sertifika doğrulaması kapatılmaz.

```bash
docker compose --profile proton up -d --build hydroxide api scheduler
docker compose exec -T scheduler python -m ai_news_radar.notifications.email
```

Hemen tek günlük özet göndermek için aşağıdaki komut kullanılabilir; saati atlar, aynı günün başarılı kaydını silmez:

```bash
docker compose exec -T scheduler python -m ai_news_radar.notifications.email --send-now
```

Saat 16:00'dan sonra ilk etkinleştirme veya yeniden başlatmada, henüz gönderilmediyse o günün özeti ilk uygun döngüde gönderilir. SMTP kabulü gelen kutusuna teslim garantisi değildir; ilk gönderimde Proton Gönderilenler ve alıcının spam klasörü kontrol edilmelidir.

## Sonuç belirsizse

Birden fazla işçi aynı günlük özeti gönderemez: önce benzersiz günlük kayıt alınır. Açık SMTP reddinde 5 dakika sonra yeniden denenir. DATA sırasında bağlantı koparsa veya süreç SMTP teslimi sırasında durursa `uncertain` / `sending` kaydı otomatik tekrar gönderimi engeller. Önce Proton Gönderilenler incelenir; gönderilmediği kesinleşirse ilgili giriş bakım işlemiyle yeniden denemeye alınabilir. Gönderim kaydı körlemesine silinmemelidir.

## Bilgisayardan bağımsız çalışma

Yerel Docker kurulumu bilgisayar kapalıyken çalışmaz. Bulutta da aynı zamanlayıcı ve hydroxide'ın sürekli çalışması, veritabanına erişmesi ve hydroxide oturumunun kalıcı depoda korunması gerekir. Yalnızca web arayüzünü yayımlamak gönderimi etkinleştirmez.
