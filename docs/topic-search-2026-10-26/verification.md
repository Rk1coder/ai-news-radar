# Konu araması doğrulaması — 26 Ekim 2026

- Başlıkla sınırlı eski aramada yeni API testleri dört davranışta başarısız oldu; frontend testleri arşiv bağlantısı ve sıralamada başarısız oldu. Uygulama sonrasında geçti.
- Son tam kontrol: `DATABASE_URL=sqlite:// .venv/bin/python -m pytest -q`: **38 passed**. `npm --prefix frontend test`: **17 passed**. `git diff --check`: temiz.
- Bağımsız kod incelemesi Türkçe sektör sözlüğündeki eksikleri buldu; 17 mevcut arayüz etiketiyle regresyon testi önce başarısız oldu, karşılıklar tamamlandıktan sonra geçti.
- Gerçek yerel PostgreSQL/API arşivi: `bilgisayarlı görü` ve `computer vision`, tüm zamanlarda aynı 13 kaydı döndürdü. Bugün: 0, arşiv önerisi: 13. `bilgisayarlı görü sağlık`: 5; `dogal dil isleme`: 3.
- Tarayıcıda ana sayfadan arama gönderildi; tarih korundu, arşivdeki 13 haber bağlantısı açıldı ve sorgu/sıralama korundu. Masaüstü ve 390×844 mobil ekranları görsel kontrol edildi (desktop.jpg, mobile.jpg).
- Yeni servis, veritabanı şeması veya LLM çağrısı eklenmedi. API ve frontend yerel Docker ortamında yeniden oluşturuldu. İnternete dağıtım, commit veya push yapılmadı.

## Sınırlar

Konu genişletme tanımlı sözlüğe dayanır. Keyfi tüm eş anlamlıları, yazım hatalarını veya serbest soruları anladığı iddia edilmez. Sonuçlar içerikteki kelime eşleşmesine dayanır; teknik terimden yalnızca bahseden bir sürüm notu da eşleşebilir. Genel asistan araması bu değişikliğe dahil değildir. Mevcut küçük arşiv için aday kayıtlar uygulamada değerlendirilir; büyük arşiv için indeksli arama gerekir.
