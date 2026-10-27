# Telegram haber akışı doğrulaması — 26 Ekim 2026

## Uygulanan davranış

Yeni, kaynak politikasıyla kabul edilmiş haberlerden kısa Türkçe başlık/özet, kaynak/yayın tarihi ve orijinal bağlantı üretimi. Ek LLM isteği yok. Kalıcı kuyruk haberle aynı transaction'da yazılıyor; scheduler tek mesaj/döngü gönderiyor. Eski arşiv geri doldurulmuyor; başarılı kayıtlar ve eski hedefin kayıtları tekrar gönderilmiyor.

## Kontroller

- İlk testler biçim ve kuyruk eksiklerini yakaladı: 8 başarısız test. Uygulamadan sonra geçti.
- Scheduler döngüsünün otomatik tarama kapalıyken de gönderim yapması için test önce başarısız oldu, bağlantı kurulduktan sonra geçti.
- Bağımsız inceleme `retry_after` süresinin HTTP yanıtından önce başlaması sorununu buldu. Gecikmeli yanıt testi 10 saniyelik hatayı gösterdi; süre yanıt alındıktan itibaren hesaplanacak şekilde düzeltildi.
- Son tam test: `DATABASE_URL=sqlite:// .venv/bin/python -m pytest -q` → **47 passed**; `npm --prefix frontend test` → **17 passed**; `git diff --check` temiz.
- Telegram HTTP testleri sahte yanıtlarla çalıştırıldı: başarı, yeniden başlatma, 429, açık 403 reddi, ağ zaman aşımı, gönderim sırasında kapanma, hedef izolasyonu ve ortak kilit.
- Gerçek yerel arşivden `python -m ai_news_radar.notifications.telegram --preview` ile mesaj biçimi doğrulandı. Önizleme gönderim yapmaz.

## Etkinleştirme durumu

> Güncelleme: Kullanıcı botu RADAR kanalına ekledi; entegrasyon etkinleştirildi ve ilk gerçek haber başarıyla gönderildi. Ayrıntılar: [activation.md](activation.md). Aşağıdaki kapalı durum kaydı ilk geliştirme aşamasına aittir.

Bot tokenı ve kanal/grup hedefi verilmedi. `TELEGRAM_ENABLED=false`, `configured=false`, kuyruk boş. Gerçek Telegram API'sine mesaj gönderilmedi; canlı kanal teslimi henüz doğrulanamadı. API ve scheduler yerel Docker ortamında bu kapalı ayarla yeniden oluşturuldu. Kullanıcı botu kanala/gruba ekleyip gerekli gönderim yetkisini vermeli; token ve hedef .env içinde ayarlanmalı. Sonrasında etkinleştirme ve ilk gerçek gönderim kontrolü yapılabilir.

`unknown` kayıtlar otomatik yeniden gönderilmez: ağ hatasında Telegram'ın mesajı kabul edip etmediği kesin bilinemez. Kanal kontrolü gerekir. Bu durum ve başarısız kayıt sayıları yerel durum komutundan görülebilir. Telegram gönderimi için Docker ve scheduler açık kalmalı.

Resmî kaynaklar: https://core.telegram.org/bots/api#sendmessage ve https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
