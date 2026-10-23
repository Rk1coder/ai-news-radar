import json
from dataclasses import dataclass

from anthropic import Anthropic

from ai_news_radar.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL

# Karar 3-B: taksonomi prompt icinde tutuluyor (statik kod degil) ki ekip
# "onemli ne" tanimini hizli iterasyonla guncelleyebilsin.
#
# Not: ilk versiyonda skorlar 55-80 bandinda kumelendi (model "guvenli orta"
# degerlere kaciyordu). Asagidaki capa noktalari (anchor) ve "coguniluk dusuk/
# orta olmali" talimati bunu acmak icin eklendi.
SYSTEM_PROMPT = """Sen bir AI/teknoloji istihbarat analistisin. Sana bir gelismenin
basligi ve ozeti verilecek. Gorevin, bu gelismeyi uc ayri eksende 0-100 araliginda
puanlamak ve ilgili sektorleri etiketlemek.

ONEMLI: Skorlarin 0-100 araliginin TAMAMINI kullan. Her gun onlarca arXiv makalesi/
sirket duyurusu gorecegiz; bunlarin buyuk cogunlugu SIRADAN'dir ve dusuk-orta skor
almali. 70+ sadece gercekten nadir, dikkat cekici vakalar icin ayrilmali. Her seyi
55-80 bandina sikistirmak (ayrim yapmamak) bir HATADIR - aralarindaki farki gorunur
kil.

- technical_impact_score (teknik yenilik/etki):
  0-20  = Onemsiz varyasyon: bilinen sonucu tekrarlama, kucuk hiperparametre denemesi.
  21-40 = Var olan yonteme kucuk/orta iyilestirme, artimsal katki.
  41-60 = Kurulu bir paradigma icinde saglam ama donusturucu olmayan katki.
  61-80 = Onemli atilim: yeni teknik/mimari, somut ve buyuk kazanim.
  81-100 = Alani degistiren, nadir bulunan temel atilim (ör. Transformer, AlphaFold,
           GPT-3 seviyesinde). Yilda birkac kez gorulur, cogu haber buraya girmez.

- hype_score (ses getirme potansiyeli, teknik onemden BAGIMSIZ degerlendir):
  0-20  = Dar bir uzman cevresi disinda kimse fark etmez.
  21-40 = Nis teknik cevrelerde (ör. belirli bir arXiv alt-alani) ilgi gorur.
  41-60 = Teknoloji medyasinda bahsi gecer ama ana akima tasmaz.
  61-80 = Genis teknoloji medyasinde/sosyal medyada belirgin gundem olusturur.
  81-100 = Teknoloji disindaki genel medyaya bile tasan, haftalarca konusulan gelisme.

- applicability_score (gercek projelerde kullanim potansiyeli, kisa-orta vade):
  0-20  = Tamamen teorik/erken arastirma, uretime yillar uzak.
  21-40 = Ciddi ek is (buyuk olcekli dogrulama, tooling) gerekiyor.
  41-60 = ~1 yil icinde orta duzey muhendislik emegiyle pilot edilebilir.
  61-80 = Aylar icinde, makul entegrasyon emegiyle gercek projelerde kullanilabilir.
  81-100 = Suan hazir, dogrudan/kolayca entegre edilebilir (ör. aci kaynak kodu var).

Her skoru verirken, bu gelismeyi zihinsel olarak hem alanin en carpici orneklerine
hem de en sirakdan orneklerine karsi konumlandir; "ortalama bir deger ver" refleksine
direnc goster.

Ayrica sector_tags: ["defense", "healthcare", "finance", "manufacturing", "general_software", ...]
listesinden ilgili olanlari sec (birden fazla olabilir).

Son olarak basligi ve ozeti akici Turkceye cevir (title_tr, summary_tr) - duz ceviri,
yorum katma; kaynak Ingilizce degilse bile Turkce bir karsilik uret.

SADECE gecerli JSON dondur, baska hicbir metin ekleme. rationale alanini KISA tut
(en fazla 2 cumle) - uzun aciklama JSON'un kesilmesine (bozulmasina) yol aciyor:
{"technical_impact_score": int, "hype_score": int, "applicability_score": int,
 "sector_tags": [str], "rationale": str, "title_tr": str, "summary_tr": str}
"""


@dataclass
class ClassificationResult:
    technical_impact_score: int
    hype_score: int
    applicability_score: int
    sector_tags: list[str]
    rationale: str
    title_tr: str = ""
    summary_tr: str = ""

    @property
    def priority_score(self) -> int:
        # Teknik etki ve uygulanabilirlik, hype'tan daha agirlikli: amac
        # "ses getiren ama bos" gelismeleri "gercek etkisi olan" gelismelerin
        # onune gecirmemek.
        return round(
            0.45 * self.technical_impact_score
            + 0.35 * self.applicability_score
            + 0.20 * self.hype_score
        )


def classify(title: str, summary: str) -> ClassificationResult:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Baslik: {title}\n\nOzet: {summary}"}],
    )
    raw_text = message.content[0].text.strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw_text)
    return ClassificationResult(
        technical_impact_score=int(data["technical_impact_score"]),
        hype_score=int(data["hype_score"]),
        applicability_score=int(data["applicability_score"]),
        sector_tags=list(data["sector_tags"]),
        rationale=str(data["rationale"]),
        title_tr=str(data.get("title_tr", "")),
        summary_tr=str(data.get("summary_tr", "")),
    )
