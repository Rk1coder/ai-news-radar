# Telegram etkinleştirmesi — 26 Ekim 2026

Kullanıcı botun eklendiğini bildirdikten sonra Telegram API ile doğrulandı:

- Bot: @mifer_ai_news_radar_bot
- Hedef: RADAR kanalı, chat_id -1003911408150
- Üyelik: administrator; can_post_messages: true
- .env içinde doğru hedef kaydedildi, TELEGRAM_ENABLED=true yapıldı. Token bu belgeye veya Git'e yazılmadı.
- API ve scheduler yeni ayarlarla yeniden oluşturuldu.
- İlk kontrol için yalnızca en güncel kabul edilmiş haber (development 427) kuyruğa eklendi; geçmiş arşiv topluca gönderilmedi.
- Scheduler ilk kaydı otomatik gönderdi: delivery 1, Telegram message_id 4, status sent, last_error boş.
- Gönderim kaydı: 26 Ekim 2026 16:43:31 Europe/Istanbul (13:43:31 UTC).
- Sonraki manuel gönderici kontrolü idle döndü; sent kayıt tekrar gönderilmedi.

Önceki verification.md dosyasındaki 'henüz yapılandırılmadı' durumu bu etkinleştirme ile güncellendi. Yeni haberler mevcut tarama saatlerinde kuyruğa alınır; scheduler kayıtları en fazla 30 saniyede bir mesaj olarak gönderir. Docker/scheduler açık kalmalıdır.
