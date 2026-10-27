# Kaynak kapsamı doğrulaması — 26 Ekim 2026

15 yeni bağlantı eklendi; varsayılan liste 33'ten 48 kaynağa çıktı. Mevcut Hugging Face ve Ben's Bites kaynakları tekrar oluşturulmadı. API, scheduler ve frontend aynı yerel Docker projesinde yeniden oluşturuldu; API sağlıklı, scheduler heartbeat çevrimiçi ve tarama aralığı 15 dakika.

## Gerçek yayın kontrolleri

`feed-checks.json`: 15 yeni + 2 mevcut kaynağın gerçek HTTP/parser sonuçları. Kontrol hiçbirinde giriş gerektirmedi. Make'in eski `/en/blog` adresi 403 döndü; güncel `/blog` adresi ve makalelerinin JSON-LD verisi çalışıyor. Bazı açıklamalarda kaçışsız satır sonu bulundu; JSON ayrıştırıcısı bu yayın biçimini destekleyecek şekilde düzeltildi ve regresyon testi eklendi.

| Kaynak | Kullanılan adres |
|---|---|
| n8n | https://blog.n8n.io/rss/ |
| Make | https://www.make.com/blog |
| Zapier | https://zapier.com/blog/feeds/latest/ |
| The Rundown AI | https://www.therundown.ai/feed |
| Medium | https://medium.com/feed/tag/artificial-intelligence + automation, yapay-zeka, otomasyon |
| Doğuş Teknoloji Medium | https://medium.com/feed/dogus-teknoloji |
| Doğuş Teknoloji Blog | https://www.d-teknoloji.com.tr/tr/blog |
| Atalay Tech | https://atalay.tech/blog |
| r/LocalLLaMA | https://www.reddit.com/r/LocalLLaMA/new/.rss?limit=100 |
| Ollama | https://ollama.com/blog/rss.xml |
| LM Studio | https://lmstudio.ai/rss.xml |
| Civitai Education | https://education.civitai.com/feed/ |
| Stable Diffusion Art | https://stable-diffusion-art.com/feed/ |
| OpenZeka | https://blog.openzeka.com/feed/ |
| Masqot | https://www.masqot.co/feed/ |

Son 96 saatlik tarih penceresi uygulanır; yeni yayın yoksa en son bir yayın özgün tarihiyle alınır. Civitai Education'ın son besleme kaydı 18 Kasım 2025, LM Studio'nunki 18 Eylül 2026; bu tarihler güncelmiş gibi değiştirilmez. Atalay için doğrulanmış kurumsal blog kullanılır; ayrı bir Medium hesabı varsayılmaz. Medium/Reddit kaynakları sosyal teyit politikasıyla değerlendirilir.

Kapsam sınırlıdır: beslemelerin sunduğu son kayıtlar değerlendirilir. Özellikle Reddit'in 100 ve Medium etiketlerinin 10'ar kayıt sınırı nedeniyle dört günlük bütün arşiv garanti edilmez. Make, liste sayfasındaki en fazla 20 yazıyı kontrol eder.

## Otomatik kontroller

- `DATABASE_URL=sqlite:// TELEGRAM_ENABLED=false .venv/bin/python -m pytest -q`: 60 geçti.
- `npm --prefix frontend test`: 21 geçti.
- `git diff --check`: geçti.
- Yeni regresyon kapsamı: 96 saat sınırı, sıralamadan sonra limit, eski son yayın yedeği, gelecek/tarihsiz kayıtlar, HTML hata yanıtını geçerli RSS saymama, Medium etiketlerinde izleme parametresinden bağımsız URL tekrarları, JSON-LD iç içe yazılar/alan adı sınırı/yayın tarihini koruma, Make makale bağlantıları, Doğuş Türkçe tarih ve İstanbul saat dönüşümü, bozuk/eksik metadata.

İlk veritabanı taraması, mevcut ortak tarama kilidi ve `run_scan` üzerinden yalnız yeni 15 kaynağa çalıştırıldı. Bu doğrulama çalıştırmasında Telegram kapalı tutuldu.

## Kalıcı kayıt ve arayüz sonucu

Tarama #8, 26 Ekim 2026 14:53:24–14:56:20 UTC: **succeeded**, 15 başarılı kaynak,
0 başarısız kaynak, 167 yeni gelişme, özet hatası yok. PostgreSQL sorgusunda yeni
15 kaynağın tamamının `raw_items` ve `developments` kayıtları bulundu. 35 içerik
kaynak politikasıyla kabul edildi; 32 Medium ve 100 Reddit kaydı çapraz teyit bekliyor.
Toplam kayıt sayısı 418'den 585'e çıktı.

Arayüzde n8n aramasıyla 5 Türkçe haber ve özgün 22–23 Ekim tarihleri doğrulandı.
Reddit kaydı, “Teyit bekleyenleri de göster” filtresiyle görüldü. Son durumda ana
akış açıldı; “585 kayıt · Son kontrol 1 dakika önce”, “15 dakikada bir tarama”
ve sonraki 18:00 TR kontrolü gösterildi. Görsel kanıt: `n8n-proof.png`.
