# AI News Radar — UI ve Kullanılabilirlik İncelemesi

23 Ekim 2026 • Çalışan yerel uygulama: http://localhost:3000/ • Mevcut 92 kayıt üzerinde inceleme.

**Genel değerlendirme:** Koyu lacivert zemin, turkuaz vurgu ve tutarlı kart biçimleri kullanılabilir bir görsel temel oluşturuyor. Ancak arayüz, günlük haber takibi yapan bir kullanıcının “Bugün ne önemli, neden önemli, kaynağı ne?” sorularını hızlı yanıtlayamıyor. Öncelikli ihtiyaç; bilgi hiyerarşisi, mobil akış, okunabilirlik ve güven açıklamalarını düzeltmek. Yalnızca renkleri veya köşe yuvarlaklıklarını değiştirmek yeterli olmaz.

**Kapsam ve yöntem:** Çalışan arayüz tarayıcıda açıldı; masaüstü ana ekran, haber önizlemesi, sohbet girişi, Türkçe arama, doğrulama filtresi ve 390 × 844 mobil görünüm incelendi. Dokuz ekran görüntüsü bu inceleme sırasında kaydedilip açılarak kontrol edildi. Davranışların nedenleri mevcut kaynak koduyla karşılaştırıldı. Ürün kodunda değişiklik yapılmadı.

**Kullanıcı hedefi:** İlgili AI gelişmelerini kısa sürede taramak, sektörüne göre daraltmak, güvenilirlik ve önemini anlamak, seçtiği haberin detayına veya kaynağına ulaşmak.

**Korunması gerekenler:** Haber kaynağı ve tarihinin kartta bulunması; teknik etki ve uygulanabilirliğin ayrı değerlendirilmesi; haber bağlamında soru sorulabilmesi; detayda belirgin bir “Habere git” eylemi. Arama alanının erişilebilir etiketi, sohbetin canlı bildirim alanı ve yerel dialog kullanımı da olumlu. Sohbet girişinde odak göstergesi görüldü ve Escape ile kapatma çalıştı.

**İncelenen adımlar**

| Adım | Ekran / işlem | Durum |
|---|---|---|
| 1 | Masaüstü ana ekran ve haber tarama | Çalışıyor; yoğunluk ve hiyerarşi zayıf |
| 2 | Haber başlığından önizleme açma | Çalışıyor; kaynak ve puan bağlamı eksik |
| 3 | Önizlemeden soru sorma ekranına geçiş | Giriş çalışıyor; yanıt üretimi sınanmadı |
| 4 | Görünen Türkçe başlıkla arama | Hatalı; mevcut haber bulunamıyor |
| 5 | Doğrulanmamış haberleri gösterme ve tekrar gizleme | Hatalı; seçenek kapatılamıyor |
| 6 | Mobil ilk açılış | Zayıf; ilk ekranda haber yok |
| 7 | Mobil haber listesine erişim | Zayıf; filtreler haberlerin önünü kesiyor |
| 8 | Mobil haber önizlemesi | İncelenen içerikle çalışıyor; uzun içerik ayrıca sınanmalı |
| 9 | Mobil sohbet girişi | İncelenen boyutta çalışıyor; gerçek cihaz klavyesi sınanmadı |

**Öncelik tanımları:** P1 temel görevi veya kullanıcı güvenini etkileyen sorun; P2 kullanım kalitesini belirgin düşüren sorun; P3 sonraki iyileştirme fırsatı. Eforlar göreli değerlendirmedir, teslim süresi taahhüdü değildir.

| No | Öncelik | Sorun | Etki | Göreli efor |
|---|---|---|---|---|
| 1 | P1 | Türkçe başlıklar aranamadığı için mevcut haber bulunamıyor | Temel keşif akışı bozuluyor | Düşük–orta |
| 2 | P1 | Doğrulanmamışları göster filtresi kapatılamıyor | Kullanıcı sonuçları kontrol edemiyor | Düşük |
| 3 | P1 | Mobilde haber akışı yaklaşık 1.929 px aşağıda başlıyor | Ana içeriğe erişim gecikiyor | Orta |
| 4 | P1 | “Doğrulandı” etiketi yöntemi olduğundan güçlü anlatıyor | Güven düzeyi yanlış yorumlanabiliyor | Düşük–orta |
| 5 | P1 | Güncelleme hatası başarı mesajına dönüşebiliyor | Güncellik hakkında yanlış güven oluşabiliyor | Orta |
| 6 | P2 | Haftalık özet uzun, kaynak bağlantıları ve dönem sınırı belirsiz | Tarama ve izlenebilirlik zayıflıyor | Orta |
| 7 | P2 | Kartlarda haber özeti yerine puan gerekçesi baskın | Kullanıcı haberi anlamadan değerlendirmesini okuyor | Orta |
| 8 | P2 | Türkçe/İngilizce karışımı ve ham sistem etiketleri | Ürün bitmemiş izlenimi veriyor | Düşük–orta |
| 9 | P2 | Küçük, soluk yardımcı metinler | Kaynak, tarih ve puanların okunması zorlaşıyor | Düşük |
| 10 | P2 | Puanların anlamı ve hesaplanışı açıklanmıyor | Kullanıcı puanla karar veremiyor | Düşük–orta |
| 11 | P2 | Filtreler dağınık, sıfırlama ve boş durum kurtarma yok | Arama deneme maliyeti artıyor | Orta |
| 12 | P2 | Detay ve sohbet akışında bağlam ve erişilebilir ad eksikleri | Kullanıcı yönünü ve bağlamını kaybedebiliyor | Orta |
| 13 | P3 | Çok uzun liste, sahte seçili kart görünümü | Tarama ve durum algısı zayıflıyor | Düşük–orta |

**1. Türkçe başlık araması — Adım 1 ve 4, davranışla doğrulandı.** Ana ekranda “NVIDIA Cosmos: Dünya Modellerini Eğitmek…” başlığı var. “Dünya Modellerini” araması 0 / 92 sonuç döndürüyor. Sunucu yalnızca orijinal `RawItem.title` alanında arıyor. Kullanıcının gördüğü Türkçe başlık da aranmalı; boşluklar ve Türkçe büyük/küçük harf davranışı tutarlı olmalı. Başlık aramasının kapsamı açık kalmalı; özet araması eklenirse alanın adı buna göre değişmeli. Kabul ölçütü: Görünen başlıktan alınan bu ifade ilgili haberi getirir. [Kaynak kod](/home/rabia/ai-news-radar/src/ai_news_radar/web/app.py:159).

**2. Kapatılamayan filtre — Adım 5, davranışla doğrulandı.** Seçenek açılınca 92 kayıt gösteriliyor. İşaret kaldırıldığında sayfa tekrar işaretli ve 92 kayıtla dönüyor. Aynı isimde gizli, işaretli bir checkbox gönderilmeye devam ediyor. Bu alan kaldırılmalı ve filtre için tek değer kaynağı kullanılmalı. Kabul ölçütü: Açınca 92, kapatınca mevcut veriyle 85 kayıt görülür ve URL ile checkbox durumu eşleşir. [Kaynak kod](/home/rabia/ai-news-radar/frontend/views/index.ejs:207).

**3. Mobil ana içerik çok aşağıda — Adım 6 ve 7, ölçüldü.** 390 × 844 görünümünde ilk haberin üst kenarı belge başlangıcından yaklaşık 1.929 px aşağıda. Üst bölüm, uzun özet ve 240 px genişliğini koruyan filtre paneli haberlerin önüne diziliyor. İlk haber kartı da yaklaşık 482 px yüksekliğinde. Mobilde kısa bir başlık alanı, açılır özet, arama ve “Filtreler” düğmesi kullanılmalı; sektör ve kaynak filtreleri açılır panelde gösterilmeli. Kabul ölçütü: Aynı boyutta ilk haber başlığı ilk ekran içinde görünür; filtre paneli kapalıyken içerik erişimini engellemez. [Yerleşim kodu](/home/rabia/ai-news-radar/frontend/views/index.ejs:74).

**4. Doğrulama rozeti gerçek yöntemi anlatmıyor — Adım 1, görsel + kod kanıtı.** Yeşil “Doğrulandı” rozeti haberin bağımsız kaynaklarla teyit edildiği izlenimi yaratabiliyor. Mevcut kod, çapraz doğrulama gerektirmeyen kaynakları doğrudan kabul ediyor; çapraz teyit mantığı diğerlerinde henüz devrede değil. Haber iddialarının gerçekliği bu denetimde araştırılmadı. Öneri: “Kaynak politikasıyla kabul edildi”, “Çapraz teyit bekliyor” gibi gerçek yöntemi açıklayan durumlar; detayda yöntem ve dayanak bağlantıları. “Bağımsız teyit edildi” ancak gerçekten sağlanıyorsa kullanılmalı. Kabul ölçütü: Rozet her kayıt için uygulanan kontrolü doğru anlatır. [Doğrulama kuralları](/home/rabia/ai-news-radar/src/ai_news_radar/verification/rules.py:19).

**5. Güncelleme akışında yanıltıcı geri bildirim riski — Adım 1'deki Güncelle eylemi, kod incelemesi.** API başarısız HTTP yanıtı döndürdüğünde frontend bunu `refreshed: 0` olarak ele alıyor; arayüz “Yeni gelişme bulunamadı, her şey güncel” diyor. Bu senaryo canlı serviste tetiklenmedi. Güncelleniyor, başarı, yeni haber yok ve hata durumları ayrılmalı; son başarılı güncelleme korunmalı ve yeniden deneme sunulmalı. İstek sürerken yinelenen gönderimler engellenmeli. Kabul ölçütü: API hatası hiçbir zaman “her şey güncel” mesajı üretmez. [Sunucu](/home/rabia/ai-news-radar/frontend/server.js:74), [mesaj](/home/rabia/ai-news-radar/frontend/views/index.ejs:188).

**6. Haftalık özet hem fazla yer kaplıyor hem dönemini belirsiz anlatıyor — Adım 1 ve 6.** Uzun paragraf masaüstünde ana akışı aşağı itiyor, mobilde ilk ekranın çoğunu dolduruyor. “15 gelişmeye dayanıyor” ifadesinden bu haberlere ulaşılamıyor. Ayrıca kod haftayı yayın tarihine göre değil, sisteme alınma tarihine göre belirliyor; özetin sözünü ettiği DeepSeek haberi listede 09.09.2026 tarihli. Bu tek başına haberin yanlışlığını göstermez, dönem etiketinin yanıltıcı olabileceğini gösterir. Öneri: Varsayılan kısa özet, “Tamamını gör”, ilgili haberlere bağlantı; yayın haftası ile tarama haftasını açık ayırma. [Özet seçimi](/home/rabia/ai-news-radar/src/ai_news_radar/classification/digest.py:19).

**7. Haber kartının hiyerarşisi ters — Adım 1 ve 7.** Başlıktan sonra sektör etiketleri, geniş ve silik “Sor” düğmesi, üç puan çubuğu ve italik puan gerekçesi geliyor. Kullanıcının “Ne olmuş?” sorusunu yanıtlayan haber özeti detay penceresinde saklı. Önerilen sıra: kaynak/tarih → başlık → iki satır haber özeti → kısa “Neden önemli?” → detay/kaynak/soru eylemleri. Alt puanlar ve uzun gerekçe isteğe bağlı açılmalı. Böylece aynı alanda daha fazla haber anlamlı biçimde taranabilir. Görsel eklemek her kart için zorunlu değil; önce bilgi sırası düzeltilmeli.

**8. Dil ve metin kalitesi — Adım 1, 2 ve 7.** `general_software`, `autonomous_systems`, `healthcare` gibi ham değerler; İngilizce gerekçeler; Türkçe cümlelerde “applicability”, “solid”, “leaderboard” gibi karışımlar var. “Pipeline / ingestion → verification → classification → DB” son kullanıcıya uygulama iç yapısını anlatıyor. Öneri: sabit Türkçe etiket sözlüğü (“Yazılım”, “Otonom sistemler”, “Sağlık”), daha doğal içerik dili, model çıktıları için metin kalite kontrolü. İşlem hattı açıklaması gerekirse yardım alanına taşınmalı. Özel marka adları çevrilmeden korunmalı.

**9. Okunabilirlik ve erişilebilirlik — Adım 1–9.** Kaynak/tarih/rozetler 11 px; puan çubuğu etiketleri 10 px; gerekçeler 12,5 px ve italik. Kaynak ve meta metninde kullanılan `#64748B`, standart kart zemini `#0D1526` üzerinde yaklaşık 3,83:1 kontrast veriyor; aynı zeminde `#94A3B8` yaklaşık 7,11:1. Bunlar kod renklerinden hesaplandı; bütün durumların uygunluk testi yapılmadı. Yardımcı metinler büyütülmeli ve kontrast artırılmalı; uzun gerekçede italik kaldırılmalı. Mobil “Sor” düğmesi ölçümde 24 px yüksekliğinde; kullanım rahatlığı için yaklaşık 44 px dokunma alanı hedeflenmeli. Gizli orijinal metin checkbox'ının görünür etiketine klavye odağı stili eklenmeli. Filtrelerin seçili durumları yalnızca renkle anlatılmamalı.

**10. Puanlar açıklamasız — Adım 1 ve 7.** “66 öncelik” ve “Hype 68” kullanıcının bu puanı nasıl yorumlayacağını anlatmıyor. Ölçek ve yapay zekâ tarafından üretildiği belirtilmeli; “Puan nasıl hesaplanıyor?” açıklaması eklenmeli. Kodun mevcut ağırlıkları teknik etki %45, uygulanabilirlik %35 ve hype %20. Hype'ın yüksek olmasının olumlu mu yoksa dikkat gerektiren bir durum mu olduğu ürün dilinde netleştirilmeli. Min. öncelik alanına ölçek yardımı ve anlaşılır hazır seçenekler eklenebilir. [Puan hesabı](/home/rabia/ai-news-radar/src/ai_news_radar/classification/llm_classifier.py:74).

**11. Filtreler ve boş durum — Adım 4 ve 5.** Arama, sayı alanı, sıralama, doğrulama seçeneği ve dil seçeneği aynı araç çubuğunda; sektör/kaynak başka alanda. Bir kısmı Uygula ile, bir kısmı anında çalışıyor. Aktif filtre özeti ve “Tüm filtreleri temizle” yok. Boş sonuç yalnızca bir cümle gösteriyor, sonraki adımı sunmuyor. Kaynak türü sayıları da filtreli sonuçlar yerine tüm veritabanını temsil ediyor. Öneri: arama/sıralama ana sırada; diğerleri bir filtre alanında; aktif seçimler kaldırılabilir etiketler halinde. Boş durumda arama ifadesi ve filtreler gösterilip “Aramayı temizle” / “Filtreleri sıfırla” sunulmalı. Sayıların hangi kapsama ait olduğu açık olmalı.

**12. Detay ve sohbet bağlamı — Adım 2, 3, 8 ve 9.** Detayda kaynak adı, yayın tarihi, doğrulama yöntemi ve puan açıklaması birlikte görünmüyor. Başlığın bir önizleme açtığı yalnızca etkileşimden sonra anlaşılıyor. Dialog'ların başlıkla `aria-labelledby` bağlantısı yok; erişilebilir adları açıkça bağlanmalı. Sohbet başlangıcında “Kısaca özetle”, “Teknik yenilik ne?”, “Kimler için önemli?” gibi örnek sorular yararlı olur. Koda göre her açılışta sohbet geçmişi sıfırlanıyor; kullanıcıya bu davranış açıklanmalı veya oturum içinde korunmalı. Yanıt kalitesi, hata sonrası yeniden deneme, eşzamanlı gönderimler ve gerçek mobil klavye ayrıca sınanmalı. [Dialog yapısı](/home/rabia/ai-news-radar/frontend/views/index.ejs:351), [sohbet açılışı](/home/rabia/ai-news-radar/frontend/views/index.ejs:418).

**13. Liste ölçeği ve seçili görünümü — Adım 1 ve 7.** Başlangıçta 85 haber tek listede; son masaüstü ölçümünde belge yaklaşık 23.611 px yüksekliğinde. Sayfalama veya “Daha fazla göster” taramayı yönetilebilir hale getirir. İlk kart, kullanıcı seçmeden `selected` sınıfıyla vurgulanıyor; bu gerçek seçim değil. Vurgu “En yüksek öncelik” gibi anlamlı bir etikete bağlanmalı veya kaldırılmalı. Kaydet/okundu işaretleri sonraki aşama fırsatıdır; temel sorunlar çözülmeden kapsam büyütülmemeli. [Kart seçimi](/home/rabia/ai-news-radar/frontend/views/index.ejs:276).

**Önerilen uygulama sırası**

1. Türkçe arama ve kapanmayan filtreyi düzelt; güncelleme hatasını başarıdan ayır; güven etiketlerini gerçek yönteme uyarla.
2. Mobilde özet ve filtreleri daralt; ilk haberi ilk ekrana getir; metin kontrastını ve dokunma alanlarını iyileştir.
3. Kartları haber özeti odaklı düzenle; etiketleri Türkçeleştir; puan açıklamasını, aktif filtreleri ve kurtarılabilir boş durumu ekle.
4. Detay/sohbet bağlamını tamamla; uzun listeyi böl; klavye, ekran okuyucu, uzun içerik ve gerçek mobil cihaz kontrollerini yap.

**Kanıt sınırları:** Ekranlar çalışan yerel sürüme aittir. Haberlerin doğruluğu dış kaynaklarla teyit edilmedi. Güncelle düğmesiyle veri toplama başlatılmadı, sohbet sorusu gönderilmedi; bunların uçtan uca çalıştığı iddia edilmiyor. Gerçek mobil cihaz, ekran klavyesi, ekran okuyucu, bütün ekran genişlikleri, büyütme, uzun sohbet ve ağ arızası senaryoları sınanmadı. Bu rapor tam erişilebilirlik uygunluk beyanı veya performans testi değildir. Koddan saptanan riskler, canlı etkileşimle doğrulanan hatalardan ayrı belirtildi.

**Ekran kanıtları — akış sırasıyla**

**1. Masaüstü ana ekran:** Tutarlı renkler; uzun özet, yoğun kartlar, ham sektör etiketleri ve küçük meta metinleri.

![1. Masaüstü ana ekran](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/01-dashboard.jpg)

**2. Haber önizlemesi:** Görsel, başlık, özet ve kaynak bağlantısı mevcut; kaynak/tarih ve doğrulama bağlamı eksik.

![2. Haber önizlemesi](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/02-preview.jpg)

**3. Sohbet girişi:** Odak göstergesi ve gönderme alanı mevcut; örnek sorular yok. Yanıt üretimi sınanmadı.

![3. Sohbet girişi](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/03-chat.jpg)

**4. Türkçe arama / boş sonuç:** Ekranda bulunan “Dünya Modellerini” ifadesiyle 0 sonuç; temizleme eylemi yok.

![4. Türkçe arama sorunu](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/04-search-empty.jpg)

**5. Kapatma girişiminden sonra filtre:** Seçenek işaretli kalıyor ve 92 kayıt gösteriliyor.

![5. Kapatılamayan doğrulama filtresi](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/05-filter-stuck.jpg)

**6. Mobil ilk ekran:** Özet ekranı dolduruyor; haber görünmüyor.

![6. Mobil ilk ekran](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/06-mobile-entry.jpg)

**7. Mobil haber listesi:** Öncesinde uzun filtre paneli; kart içinde çok satırlı etiketler ve alt alta kırılan puanlar.

![7. Mobil haber listesi](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/07-mobile-feed.jpg)

**8. Mobil önizleme:** İncelenen haberin eylemleri görünür; içerik uzunluğu arttığında ayrıca sınanmalı.

![8. Mobil önizleme](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/08-mobile-preview.jpg)

**9. Mobil sohbet girişi:** Giriş ve Gönder görünür; gerçek ekran klavyesi ve uzun yanıtlar kapsam dışında.

![9. Mobil sohbet girişi](/home/rabia/ai-news-radar/docs/ui-audit-2026-10-23/09-mobile-chat.jpg)
