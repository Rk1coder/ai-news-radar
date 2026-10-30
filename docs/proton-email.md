# Radar günlük özeti — Proton / hydroxide

Günlük saat: **13:00 Europe/Istanbul**. Önizleme gönderim yapmadan hazırlanabilir. Hesap bağlantısı tamamlanmadan `EMAIL_ENABLED` kapalı kalmalıdır.

## Bülten düzeni

Bülten, web sitesinin açık renk paletini (`frontend/public/styles.css`) kullanır:
beyaz zemin, antrasit metin (`#17191c`), turkuaz Radar başlığı ve bağlantılar
(`#0a7f7c`), şeftali özet alanı (`#fbe1d1`) ve koyu kahverengi özet başlığı
(`#5d2a1a`). Kompakt logo şeffaf ve turkuazdır. Bölüm girişleri
masaüstünde başlık/özet olarak iki sütunludur; telefonda tek sütuna dönüşür.
Desteklenen kaynaklarda, bülten hazırlanırken haber sayfasının `og:image` veya
`twitter:image` kapak görseli alınır. YouTube watch/shorts/live/youtu.be bağlantılarında
video kimliğinden küçük resim alınır. WebP ve ICO görselleri Pillow ile PNG/JPEG'e
dönüştürülür; animasyonlarda ilk kare kullanılır. Görseller CID eki olarak e-postaya
gömülür; kaynak adı gösterilir ve görsele tıklanınca haber açılır. Kapak bulunamazsa
resmî sayfanın apple-touch-icon/favicon görseli denenir ve **Kaynak logosu** olarak
etiketlenir; bir haber fotoğrafı gibi sunulmaz. Kaynak logosu da alınamazsa haber
metni korunur, boş görsel alanı oluşturulmaz. Görsel alma
işlemi veri tabanını değiştirmez; HTML ve MIME önizlemeleri aynı görselleri kullanır.

Görsel toplamada yalnızca `notifications/email_images.py` içindeki yayıncı ve CDN
adreslerine HTTPS ile erişilir. Yönlendirmeler ve IP adresleri kontrol edilir.
En fazla 12 haber, indirilen dosya başına 2 MB, e-postaya gömülen görsel başına
900 KB, toplam 4 MB ve 25 saniyelik ağ işlem bütçesi uygulanır. Dört indirme işçisi
kapakları paralel işler; logo aşaması için süre ayrılır. Aynı kaynağın logosu
bülten hazırlanırken yalnızca bir kez alınır. 16 milyon piksel üzerindeki görseller
reddedilir; büyük görseller küçültülür. SVG dönüştürülmez ve atlanır.
Yeni yayıncı/CDN eklenirse bu izin listesi de güncellenmelidir.
Haberler `LLM & Yerel Modeller`, `Araştırma` ve `Araçlar & Uygulamalar` başlıklarında
yerel kurallarla gruplanır; boş başlıklar gösterilmez. Bu konulara uymayan haberler
`Diğer gelişmeler` altında korunur. Akademik kaynaklar araştırma bölümüne öncelikle
yerleştirilir; bölüm içindeki haber sırası değişmez.

Seçili haberler içinde doğrudan GitHub proje/Hugging Face model veya uygulama
bağlantısı ya da desteklenen resmi araç yayını varsa, bir tanesi `Bugün
denenebilecekler` olarak kendi bölümünde vurgulanır. Haber ikinci kez eklenmez.
Bekleme listesi ve henüz erişime açılmadığı belirtilen duyurular önerilmez;
mevcut özet ve bağlantı kullanılır, yeni içerik veya bağlantı üretilmez.

Okuma süresi, bültende gösterilen metin uzunluğu üzerinden dakikada yaklaşık
200 kelime ile hesaplanır ve yukarı yuvarlanır. Haber yoksa süre ve öneri
gösterilmez. Konu başlıkları, öneri ve süre düz metin alternatifinde de bulunur.

## Hazır kurulum

Hydroxide'ın [GitHub deposu](https://github.com/emersion/hydroxide) [Codeberg'e taşındı](https://codeberg.org/emersion/hydroxide). Yerel imaj resmî Codeberg `02b3b6c8aff726d2404b6ed5f6ba1b7937e1f30e` revizyonundan derlenir. `proton` Compose profili SMTP köprüsünü açar; hosta SMTP portu yayınlanmaz. Hesap oturumu `hydroxide-auth` volume'ünde saklanır. Bu volume ve köprü parolası korunmalıdır.

Bu revizyon, `Content-Disposition: inline` görsellerini metin parçası sayıp HTML'den
sonra atlar ([upstream #191](https://github.com/emersion/hydroxide/issues/191)).
`deploy/hydroxide/inline-images.patch` ve `inline_images.go`, Content-ID içeren
görselleri köprünün şifreli ek yükleyicisine yönlendirir. CID, dosya adı, görsel
baytları ve özgün inline başlığı korunur; logo ve haber kapakları birlikte düzelir.
Radar, Proton'un ContentID doğrulaması için her görsele `@radar.local` alanı
içeren benzersiz bir MIME kimliği üretir; HTML'deki CID ile ek başlığı eşleştirilir.
Köprü, MIME kimliğinin dışındaki `< >` işaretlerini Proton API'sine iletmeden
çıkarır; API, HTML'deki `cid:` sonrasında kullanılan yalın kimliği bekler.
Proton'un ek imzası zorunluluğu için `sign_attachments.go` açık görsel baytlarına
gönderen anahtarıyla ayrık OpenPGP imzası üretir. `attachment-signatures.patch`
bu imzayı yüklemedeki `Signature` dosya alanına ekler; şifreleme korunur.
Derlemede `go test ./smtp ./protonmail`, MIME yönlendirmesini, CID dönüşümünü,
imzanın doğrulanmasını/değiştirilmiş baytların reddini ve yükleme biçimini sınar.
Önceden gönderilmiş, görselleri atılmış e-postalar bu değişiklikle onarılmaz.

```bash
docker compose --profile proton build hydroxide
docker compose --profile proton up -d hydroxide
```

## Hesabı bağlama — kullanıcının terminalinde

Tek komutla giriş yapıp yalnızca bir deneme özeti göndermek için, proje klasöründeki yardımcıyı kendi terminalinizde çalıştırabilirsiniz:

```bash
python3 scripts/connect_proton.py --account your-address@proton.me --recipient recipient@example.com --send-test
```

Proton giriş parolası hydroxide'ın etkileşimli alanına girilir. Başarılı giriş sonunda verilen `Bridge password`, yardımcının sonraki gizli alanına yapıştırılır. Yardımcı, uygulama ve zamanlayıcı kapalı olsa da geçici bir konteynerle SMTP kimlik doğrulamasını yapar ve köprü parolasını `.env` içine korumalı olarak kaydeder; Proton giriş parolasını kendisi kaydetmez. `--send-test` yalnızca o deneme işlemi için maili açar, kalıcı günlük gönderim kapalı kalır. Gönderim yalnızca komutta belirtilen alıcıya yapılır. Alıcı belirtilmezse gönderen hesabına deneme yapılır. Aşağıdaki adımlar aynı bağlantının elle kurulumudur.

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
EMAIL_SEND_HOUR=13
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

Saat 13:00'ten sonra ilk etkinleştirme veya yeniden başlatmada, henüz gönderilmediyse o günün özeti ilk uygun döngüde gönderilir. SMTP kabulü gelen kutusuna teslim garantisi değildir; ilk gönderimde Proton Gönderilenler ve alıcının spam klasörü kontrol edilmelidir.

## Sonuç belirsizse

Birden fazla işçi aynı günlük özeti gönderemez: önce benzersiz günlük kayıt alınır. Açık SMTP reddinde 5 dakika sonra yeniden denenir. DATA sırasında bağlantı koparsa veya süreç SMTP teslimi sırasında durursa `uncertain` / `sending` kaydı otomatik tekrar gönderimi engeller. Önce Proton Gönderilenler incelenir; gönderilmediği kesinleşirse ilgili giriş bakım işlemiyle yeniden denemeye alınabilir. Gönderim kaydı körlemesine silinmemelidir.

## Bilgisayardan bağımsız çalışma

Yerel Docker kurulumu bilgisayar kapalıyken çalışmaz. Bulutta da aynı zamanlayıcı ve hydroxide'ın sürekli çalışması, veritabanına erişmesi ve hydroxide oturumunun kalıcı depoda korunması gerekir. Yalnızca web arayüzünü yayımlamak gönderimi etkinleştirmez.

## Türkçe anlatım

Başlıklar, özetler ve önem açıklamaları için Türkçe karakterlerin korunması, cümle düzeninde başlıklar ve edilgen haber dili kullanılması çeviri talimatlarına eklenmiştir. İddiaların kaynağı, belirsizlikler, tarihler, sayılar ve model sürümleri korunur. Bu talimatlar yeni çevirilerde uygulanır; önceden kaydedilmiş haberler kendiliğinden yeniden yazılmaz.
