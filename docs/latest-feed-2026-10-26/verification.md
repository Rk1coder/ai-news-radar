# Son haberler, güncelleme ve yazı logosu

## Yapılanlar
- Varsayılan ana sayfa tüm tarihlerdeki haberleri En yeni sırasıyla açar. Bugün ve Son 7 gün filtreleri kullanıcı seçimine bağlıdır; aramada ilgi sıralaması korunur.
- Hugging Face Blog RSS beslemesi doğrulandı. Substack AI konu sayfasının herkese açık posts metaverileri için ayrı bağlayıcı eklendi; tarihleri UTC'ye çevirir, URL tekrarlarını ve geçersiz URL'leri eler, en yeni 15 yazıyı alır. Eksik/bozuk sayfa kaynak hatasıdır.
- Zamanlama 15 dakikaya ayarlandı; SCAN_INTERVAL_MINUTES=0 eski saat listesini kullanır.
- Manuel tarama DB kilidini aldıktan ve run kaydını yazdıktan sonra 202 döner. Arayüz sayfa değiştirmeden başlatır; tarama sırasında 10sn, normalde 60sn kontrol eder. Kaynak tamamlandıkça ilerleme sayıları kaydedilir.
- Kullanıcı font kullanımına izin verdiği için arka plansız RADAR ve alt başlık gerçek metin olarak uygulandı. Asistan radar simgesi korundu. Favicon şeffaf R harfidir.

## Doğrulama
- İzole DB ve TELEGRAM_ENABLED=false ile Python: 52 test geçti.
- Frontend: 21 test geçti. Canlı manuel başlatma/tamamlanma/hata, taslak ve URL korunması dahil.
- İlk gerçek tur (id 4): 40 yeni kayıt. Sonraki tur (id 5): 18 yeni kayıt; 32 kaynak başarılı, yalnız tldr-ai başarısız. Substack ilk turdaki geçici hatadan sonra 15 yazıyla kaydedildi.
- Hugging Face'in 23 Ekim tarihli yazıları ve Substack'in 25 Ekim tarihli yazıları ana akışta görünüyor. Substack kartlarının açık sayfaya reload olmadan geldiği DOM üzerinden doğrulandı.
- Mobil 390px ve masaüstü görünümü kontrol edildi: yatay taşma yok, logo resim zemini taşımıyor.
- git diff --check temiz. Yerel Docker API, scheduler ve frontend yeniden oluşturuldu; dış ortama yayın/commit/push yapılmadı.

## Sınırlar
Substack konu sayfası seçilmiş yazılardan oluşur; tüm Substack yayınları veya ücretli içerik alınmaz. Kaynaklar 15 dakikada bir taranır; bu bir push haber aboneliği değildir. TLDR beslemesindeki erişim hatası bu çalışmanın sonunda sürüyordu; diğer kaynakların taranmasını engellemez.

## Gerçek manuel işlem
Son dağıtımdan sonra tarayıcıdaki Güncelle düğmesi yaklaşık 297ms içinde “Tarama başladı” durumuna geçti. URL aynı kaldı. Sayfa yenilenmeden ilerleme 16 ve sonra 19 kaynak olarak göründü; bir yeni kayıt daha eklendi (toplam 417). Bu kullanıcı tarafından başlatılabilen tarama arka planda normal şekilde sürer; ekran kanıtları desktop.png ve mobile.png.
