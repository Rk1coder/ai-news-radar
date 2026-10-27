# Otomatik tarama ve canlı akış — doğrulama

Tarih: 26 Ekim 2026, Europe/Istanbul.

## Sonuç

Günde beş tarama (06.00/10.00/14.00/18.00/22.00), kalıcı tarama günlüğü,
Bugün/En yeni başlangıcı ve açık sayfada dakikalık güncelleme uygulanıp yerel
Docker kurulumunda etkinleştirildi. Dış sunucuya yayın yapılmadı.

- Tam Python testleri: **33 geçti**.
- Tam Node testleri: **15 geçti**.
- `git diff --check`: temiz.
- Gerçek PostgreSQL kilidi tutulurken API'nin eşzamanlı `/api/refresh` isteği
  **409** döndürdü; ikinci tarama başlamadı.
- İlk scheduler turu: planlı zaman 26 Ekim 06.00 TR, başlangıç 09.47 TR
  (başlangıçtaki kaçırılmış turu yakalama), bitiş 09.49 TR.
- İlk tur **41 yeni gelişme**, **29 başarılı kaynak**, **3 erişilemeyen kaynak**:
  `deepmind-blog`, `bens-bites`, `tldr-ai`. Sonuç `partial`; başarı diye gizlenmedi.
- Servis yeniden oluşturulup başlatıldıktan sonra scan_runs sayısı **1** kaldı;
  aynı saat dilimi tekrar taranmadı.
- Kaynak Atom tarihleri düzeltilerek mevcut **40** tarihsiz kayda gerçek kaynak
  tarihi eklendi. Yeni gelişme veya ek sınıflandırma isteği oluşturulmadı.

## Tarayıcı kontrolü

- Sayfayı yenilemeden kayıt sayısının 300 → 308 → 338 olarak değiştiği görüldü.
- Kaynak tarihleri düzeltildikten sonra açık sayfadaki Bugün listesi 34 → 3
  olarak güncellendi; geçmiş duyurular bugünün haberleri sayılmadı.
- Her iki güncelleme sırasında “Otomatik güncellemede bu taslak korunmalı.”
  sohbet girdisi aynı kaldı. Test taslağı daha sonra temizlendi.
- Bugün/En yeni varsayılanı ve Son 7 gün bağlantısının haftalık listeye geçişi
  görüldü. Son görünüm bugün listesine geri döndürüldü.
- 390 × 844 mobil görünümünde yeni tarih sekmeleri, tarama durum bilgisi,
  filtreler, haber kartları ve sohbet kapanıp açılma akışı görsel olarak incelendi.
- Ekran görüntüleri: `desktop.jpg`, `mobile.jpg`.
- Önizleme aracının ilk sekmesinde debugger bağlantısı zaman aşımına uğradı;
  yeni sekmede mobil kontrol tamamlandı. Bu yüzden eski sekmeden konsol kontrolü
  iddia edilmiyor.

## İnceleme ve regresyonlar

Bağımsız incelemedeki iki P2 odak sorunu düzeltildi: değişmeyen boş durumun
arşiv bağlantısı ve kapalı özet başlığının klavye odağı korunuyor. Testler ayrıca
geçmişten dönüşte (BFCache) polling'in devamını, yeni kartların sohbet düğmesinin
bağlanmasını, gizli/çevrimdışı kontrolünü, istek çakışmasını ve bağlantı sonrası
toparlanmayı kapsıyor. Tarih filtresi İstanbul gece yarısı sınırında test edildi.
Kaynak işlemindeki rollback sonucu eklenmeyen gelişmeler artık yeni kayıt
sayısına dahil edilmiyor.

## İşletim sınırları

Bilgisayar/sunucu ve Docker açık olmalı. Yeni içerik kaynakların yayınlamasına
bağlı; her ziyarette mutlaka yeni haber garantisi yok. Başarısız tamamlanan tur
sonraki planlı saatte tekrar denenir. Fiziksel telefon klavyesi ve 24 saat boyunca
beş turun tümünün gerçek zamanlı gözlemi yapılmadı; saat hesabı otomatik testlerle
ve gerçek başlangıç turuyla doğrulandı. Kurulum/ayarlar README.md dosyasında.
