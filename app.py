
import os
import io
import re
import time
import html
import base64
import requests
import gradio as gr
from PIL import Image


# =========================================================
# AYARLAR
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

MAX_OUTPUT_TOKENS = 12000
IMAGE_MAX_SIZE = (1200, 1200)
IMAGE_QUALITY = 82


# =========================================================
# TARİH ARAŞTIRMASI İÇİN AYRINTILI TALİMAT
# =========================================================

PROMPT = r"""
Sen deneyimli bir tarih, arkeoloji, sanat tarihi, mimarlık tarihi
ve kültürel miras araştırma asistanısın.

Görevin, yüklenen fotoğraftaki eseri tanımlamak ve hakkında
mümkün olduğunca kapsamlı, ayrıntılı, Türkçe bir araştırma raporu
hazırlamaktır.

Google Arama aracını kullanarak eserin kimliğini ve tarihini
güvenilir kaynaklardan araştır. Öncelikle müze ve resmî kurumları,
üniversiteleri, akademik yayınları, kazı raporlarını ve UNESCO gibi
kurumların kayıtlarını tercih et.

ÖNEMLİ İLKELER:
- Fotoğrafta gerçekten görülen ayrıntıları tarihsel çıkarımlardan ayır.
- Eserin kimliği kesin değilse olası kimlikleri ve gerekçelerini yaz.
- Bir eseri yalnızca görünüşüne bakarak kesin biçimde tarihlendirme.
- Bilinmeyen bilgileri uydurma.
- Gerçek olmayan kazı raporu, envanter numarası, müze kaydı,
  alıntı, tarih veya kaynak üretme.
- Kaynakların desteklemediği iddiaları kesin gerçek gibi anlatma.
- Türk tarihiyle ilgisi kanıtlanamıyorsa bunu açıkça belirt.
- Aynı bilgiyi tekrar ederek metni yapay biçimde uzatma.
- Her bölümde anlamlı, açıklayıcı ve derinlemesine bilgi ver.
- Araştırmada bulunamayan bilgileri açıkça "doğrulanamadı" diye yaz.
- Görseldeki yazılar okunamıyorsa yazıyı tahmin ederek aktarma.
- Güncel konum ve koruma durumu için güncel kaynakları tercih et.
- Mümkün olduğunda iddiaların yanına kaynak numarası [1], [2] koy.
- Raporun sonunda bu numaralarla eşleşen kaynakça hazırla.
- Rapor Türkçe olmalı; özel adları gerektiğinde özgün biçimleriyle ver.

ÇIKTI BİÇİMİ:
Aşağıdaki bölüm işaretlerini aynen kullan. Her bölümün içeriğini
işaretin hemen altına yaz. Bölümleri atlama. Yanıt uzun ve ayrıntılı
olsun. Kısa özetle yetinme.

[[GENEL_BAKIS]]

1. ESERİN TANIMLANMASI
- Muhtemel eser adı ve alternatif isimleri
- Eserin türü, ait olduğu uygarlık ve kültür
- Tahmini yapım dönemi ve bu tahminin gerekçesi
- Tanımlamanın güven düzeyi
- Fotoğraftan belirlenebilen ve belirlenemeyen özellikler
- Benzer eserlerle karıştırılma ihtimali
- Kesin teşhis için gerekli ek fotoğraflar veya bilgiler

[[GORSEL_INCELEME]]

2. FOTOĞRAFIN AYRINTILI İNCELENMESİ
- Görülebilen biçim, ölçü izlenimi, malzeme ve yüzey özellikleri
- Motifler, figürler, semboller, süslemeler ve yazılar
- Aşınma, kırılma, renk değişimi ve onarım izleri
- Fotoğrafın açı, ışık ve çözünürlük bakımından sınırlamaları
- Gözlem ile yorum arasındaki fark
- Görüntüden kesinlikle çıkarılamayacak sonuçlar

[[TARIHCE]]

3. AYRINTILI TARİHÇE
Bu bölümü uzun ve kronolojik bir tarih anlatısı olarak hazırla.

- Eserin ortaya çıktığı tarihsel ortam
- Yapıldığı dönemin siyasi ve toplumsal koşulları
- Eserin ortaya çıkışına yol açan ihtiyaç veya amaç
- Yapım süreci ve biliniyorsa yapımına katılan kişiler
- Eserin tarih boyunca geçirdiği değişimler
- Kullanımının değişmesi, terk edilmesi veya yeniden keşfi
- Varsa kazılar, restorasyonlar ve mülkiyet değişiklikleri
- Eserle ilişkili önemli tarihsel olaylar
- Günümüze ulaşma süreci
- Bu aşamalarda doğrulanabilen bilgiler ve belirsizlikler

Her tarihsel aşamayı ayrı alt başlıkla açıkla. Kaynak bulunmuyorsa
olay veya tarih uydurma.

[[KRONOLOJI]]

4. AYRINTILI KRONOLOJİ
- Eserin yapım dönemi
- İlgili uygarlığın önemli siyasi gelişmeleri
- Eserin tarihindeki önemli dönüm noktaları
- Biliniyorsa keşif, kazı, restorasyon ve müzeye alınma tarihleri
- Günümüzdeki durumu hakkında tarihli bilgiler

Mümkün olduğunda tarihleri, olayları ve önemlerini tablo biçiminde
ver. Kesin tarihi bilinmeyen olayları yaklaşık veya belirsiz olarak
işaretle. Bir olayın esere doğrudan bağlı olmadığı durumlarda bunu
açıkla.

[[MIMARI_SANAT]]

5. MİMARİ VE SANAT TARİHİ
- Mimari plan, form, oranlar ve kompozisyon
- Yapım teknikleri ve kullanılan malzemeler
- Süsleme anlayışı, motifler ve sembolizm
- Sanat üslubu ve benzer eserlerle ilişkisi
- Bölgesel ve kültürel etkiler
- Usta, atölye veya sanatçı hakkında bilinenler
- Dönemin teknik imkânları
- Eserin sonraki sanat geleneklerine etkisi
- Fotoğraftan doğrulanabilen özellikler ile literatür bilgileri

[[ARKEOLOJI]]

6. ARKEOLOJİK İNCELEME
- Biliniyorsa buluntu yeri ve arkeolojik bağlam
- Kazı geçmişi ve ilgili kazı ekipleri
- Buluntu tabakası, tarihlendirme yöntemleri ve bulgular
- Benzer buluntular ve bunların anlamı
- Eserin taşınmış, yeniden kullanılmış veya başka bir yapıdan
  getirilmiş olma ihtimali
- Envanter numarası veya katalog bilgisi bulunabiliyorsa
- Arkeolojik kanıtların sınırları ve tartışmalı yorumlar

Bu bilgileri yalnızca güvenilir kaynaklar destekliyorsa aktar.

[[TARIHSEL_BAGLAM]]

7. DÖNEMİN TARİHSEL BAĞLAMI
- Siyasi yapı ve yönetim biçimi
- Toplumsal sınıflar ve günlük yaşam
- Ekonomi, ticaret ve üretim
- Din, inanç ve ritüeller
- Askerî yapı ve bölgesel ilişkiler
- Dil, yazı, eğitim ve kültürel yaşam
- Eserin bu koşullarla ilişkisi

Genel dönem bilgisini esere ilişkin doğrudan kanıt gibi sunma.

[[TURK_TARIHI]]

8. TÜRK TARİHİYLE İLİŞKİSİ
- Eserin Türk tarihiyle doğrudan bağlantısı var mı?
- Varsa hangi Türk devleti, topluluğu veya tarihsel dönemle ilişkili?
- Selçuklu, Osmanlı, Anadolu beylikleri veya diğer Türk tarihî
  dönemleriyle bağlantı varsa bunu kaynaklarla açıkla.
- Türklerin bölgeye gelişi ve bölgenin tarihsel dönüşümüyle ilişkisi
- Mimari, sanat, dil veya kültür bakımından olası etkiler
- Eserin daha eski bir uygarlığa ait olması durumunda bunu açıkça belirt.
- Doğrudan bağlantı yoksa zorla bağlantı kurma.

[[KARSILASTIRMA]]

9. KARŞILAŞTIRMALI ESER ANALİZİ
- Benzer dönemden en az üç eser bulunabiliyorsa karşılaştır.
- Eserlerin tarihleri, konumları, malzemeleri ve üslupları
- Ortak özellikler ve belirgin farklılıklar
- Aynı kültürün ürünü olduklarının kesin olup olmadığı
- Karşılaştırmanın tarihsel anlamı

Güvenilir biçimde belirlenemeyen benzer eserleri isim uydurarak verme.

[[KORUMA]]

10. KORUMA, RESTORASYON VE KÜLTÜREL MİRAS
- Eserin bilinen güncel konumu
- Korunma durumu ve varsa riskler
- Restorasyon ve koruma çalışmaları
- Doğal etkenler ve insan faaliyetlerinin etkisi
- Kültürel miras statüsü veya resmî tescil bilgisi
- Koruma çalışmalarındaki tartışmalar
- Sürdürülebilir koruma için uzmanların yaklaşımı

Güncel bilgileri tarihli kaynaklarla destekle; teyit edemiyorsan belirt.

[[ONEM]]

11. ESERİN TARİHSEL ÖNEMİ
- Tarihçiler ve arkeologlar için önemi
- Sanat ve mimarlık tarihi bakımından değeri
- Bölgesel ve evrensel kültür mirasındaki yeri
- Günümüzdeki kültürel ve toplumsal anlamı
- Eserin geçmiş hakkında hangi soruları cevaplayabildiği
- Hangi soruların hâlâ açık kaldığı

[[BELIRSIZLIKLAR]]

12. TARTIŞMALAR VE BELİRSİZLİKLER
- Kimlik ve tarihlendirme tartışmaları
- Farklı uzman görüşleri varsa bunlar
- Kaynaklar arasındaki uyuşmazlıklar
- Fotoğraftan kesinleştirilemeyen noktalar
- Daha sağlam sonuca ulaşmak için gereken kanıtlar

[[KAYNAKLAR]]

13. KAYNAKÇA VE İLERİ ARAŞTIRMA
- Kullanılan kaynakların başlığı ve kurumu/yazarı
- Kaynağın doğrudan bağlantısı
- Kaynağın hangi iddiayı desteklediği
- Varsa yayın veya güncelleme tarihi
- Müze katalogları, akademik yayınlar ve resmî kayıtlar
- İleri araştırma için uygun arama başlıkları

Arama sırasında gerçekten ulaşılan kaynakları ayrı listele.
Yalnızca önerilen kurumları "başvurulabilecek kaynaklar" olarak ayır.
Uydurma URL, kitap adı veya yayın künyesi üretme.

[[SONUC]]

14. GENEL DEĞERLENDİRME
- Eserin kimliğine dair en güçlü sonuç
- En sağlam tarihsel çıkarımlar
- Güven düzeyi ve gerekçesi
- Araştırmanın en önemli bulguları
- Kullanıcının eseri daha iyi tanımlaması için gereken bilgiler

SON TALİMAT:
Her bölümü olabildiğince kapsamlı yaz. Toplam yanıtı bir kısa
özetle sınırlandırma. Gerektiğinde uzun açıklamalar, alt başlıklar,
madde listeleri ve karşılaştırma tabloları kullan.
"""


# =========================================================
# GEMINI API
# =========================================================

def gemini_istegi(govde):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadı. Render Environment "
            "bölümünden bu değişkeni ekle."
        )

    son_hata = "Bilinmeyen API hatası."

    for deneme in range(3):
        try:
            cevap = requests.post(
                API_URL,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json"
                },
                json=govde,
                timeout=(15, 240)
            )

            if cevap.ok:
                return cevap.json()

            son_hata = (
                f"Gemini HTTP {cevap.status_code}: "
                f"{cevap.text[:700]}"
            )

            # Kimlik doğrulama, model adı ve istek biçimi hatalarında
            # aynı isteği tekrar göndermek genellikle işe yaramaz.
            if cevap.status_code not in (408, 429, 500, 502, 503, 504):
                break

        except requests.RequestException as hata:
            son_hata = f"Bağlantı hatası: {hata}"

        if deneme < 2:
            time.sleep(2 ** (deneme + 1))

    raise RuntimeError(son_hata)


# =========================================================
# FOTOĞRAF HAZIRLAMA
# =========================================================

def fotograf_hazirla(dosya_yolu):
    with Image.open(dosya_yolu) as kaynak:
        resim = kaynak.convert("RGB")
        resim.thumbnail(IMAGE_MAX_SIZE)

        tampon = io.BytesIO()
        resim.save(
            tampon,
            format="JPEG",
            quality=IMAGE_QUALITY,
            optimize=True
        )

        return base64.b64encode(
            tampon.getvalue()
        ).decode("utf-8")


# =========================================================
# KAYNAK TOPLAMA
# =========================================================

def kaynaklari_al(cevap):
    """Gemini'nin döndürdüğü arama kaynaklarını toplar."""
    kaynaklar = []
    gorulen = set()

    for aday in cevap.get("candidates", []):
        meta = aday.get("groundingMetadata", {}) or {}

        for parca in meta.get("groundingChunks", []) or []:
            web = parca.get("web", {}) or {}
            url = web.get("uri", "")
            baslik = web.get("title", "Kaynak")

            if url.startswith("https://") or url.startswith("http://"):
                if url not in gorulen:
                    gorulen.add(url)
                    kaynaklar.append((baslik, url))

    return kaynaklar


def kaynak_listesi(kaynaklar):
    if not kaynaklar:
        return (
            "Arama kaynakları yanıtın kaynak metaverisinde "
            "bulunamadı. Aşağıdaki kurumlar yalnızca araştırma "
            "başlangıç noktalarıdır; esere ilişkin doğrulanmış "
            "kaynaklar olarak değerlendirilmemelidir.\n\n"
            "- [Kültür ve Turizm Bakanlığı](https://www.ktb.gov.tr/)\n"
            "- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)\n"
            "- [DergiPark](https://dergipark.org.tr/)"
        )

    satirlar = [
        "Aşağıdaki bağlantılar, bu yanıt sırasında arama "
        "metaverisinde döndürülen kaynaklardır. Her birinin "
        "ilgili iddiayı gerçekten desteklediğini ayrıca kontrol et.\n"
    ]

    for i, (baslik, url) in enumerate(kaynaklar, start=1):
        temiz_baslik = html.escape(baslik)
        temiz_url = html.escape(url, quote=True)
        satirlar.append(f"{i}. [{temiz_baslik}]({temiz_url})")

    return "\n\n".join(satirlar)


# =========================================================
# RAPOR BÖLÜMLERİNİ AYIRMA
# =========================================================

BOLUM_ISARETLERI = [
    ("GENEL_BAKIS", "Genel Bakış"),
    ("GORSEL_INCELEME", "Görsel İnceleme"),
    ("TARIHCE", "Ayrıntılı Tarihçe"),
    ("KRONOLOJI", "Kronoloji"),
    ("MIMARI_SANAT", "Mimari ve Sanat"),
    ("ARKEOLOJI", "Arkeoloji"),
    ("TARIHSEL_BAGLAM", "Tarihsel Bağlam"),
    ("TURK_TARIHI", "Türk Tarihi"),
    ("KARSILASTIRMA", "Karşılaştırma"),
    ("KORUMA", "Koruma ve Miras"),
    ("ONEM", "Tarihsel Önem"),
    ("BELIRSIZLIKLAR", "Belirsizlikler"),
    ("KAYNAKLAR", "Kaynaklar"),
    ("SONUC", "Genel Sonuç")
]


def raporu_bol(metin):
    bolumler = {}

    desen = r"\[\[([A-Z_]+)\]\]"
    eslesmeler = list(re.finditer(desen, metin))

    for i, eslesme in enumerate(eslesmeler):
        anahtar = eslesme.group(1)
        baslangic = eslesme.end()

        bitis = (
            eslesmeler[i + 1].start()
            if i + 1 < len(eslesmeler)
            else len(metin)
        )

        icerik = metin[baslangic:bitis].strip()

        if icerik:
            bolumler[anahtar] = icerik

    return bolumler


# =========================================================
# ANA İŞLEM
# =========================================================

def eser_ara(fotograf_yolu):
    toplam_baslangic = time.perf_counter()

    if not GEMINI_API_KEY:
        hata = (
            "## Sunucu ayarı eksik\n\n"
            "Render → Environment bölümüne `GEMINI_API_KEY` "
            "değişkenini ekle. Anahtarı Python koduna veya "
            "GitHub deposuna yazma."
        )
        return (hata,) + ("",) * 14

    if not fotograf_yolu:
        mesaj = "Lütfen önce bir eser fotoğrafı yükle."
        return (mesaj,) + ("",) * 14

    try:
        # 1. Fotoğrafı optimize et.
        foto_baslangic = time.perf_counter()
        foto_base64 = fotograf_hazirla(fotograf_yolu)
        foto_suresi = time.perf_counter() - foto_baslangic

        # 2. Araştırma isteği oluştur.
        govde = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": foto_base64
                        }
                    }
                ]
            }],
            "tools": [
                {"google_search": {}}
            ],
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": MAX_OUTPUT_TOKENS
            }
        }

        # 3. Model yanıtını al.
        api_baslangic = time.perf_counter()
        cevap = gemini_istegi(govde)
        api_suresi = time.perf_counter() - api_baslangic

        adaylar = cevap.get("candidates", [])

        if not adaylar:
            raise RuntimeError(
                "Model bir yanıt üretmedi. API yanıtı: "
                + str(cevap.get("promptFeedback", {}))[:500]
            )

        parcalar = adaylar[0].get("content", {}).get("parts", [])

        rapor = "\n".join(
            parca.get("text", "")
            for parca in parcalar
            if parca.get("text")
        ).strip()

        if not rapor:
            raise RuntimeError(
                "Model boş yanıt verdi. Model adını, API kotasını "
                "ve Render günlüklerini kontrol et."
            )

        # 4. Bölümleri ayır.
        bolumler = raporu_bol(rapor)

        # Beklenmedik biçim durumunda tüm metni kaybetme.
        if len(bolumler) < 4:
            bolumler["GENEL_BAKIS"] = rapor

        # 5. Arama kaynaklarını kaynaklar sekmesine ekle.
        kaynaklar = kaynaklari_al(cevap)
        kaynak_metni = kaynak_listesi(kaynaklar)

        if bolumler.get("KAYNAKLAR"):
            bolumler["KAYNAKLAR"] += "\n\n---\n\n" + kaynak_metni
        else:
            bolumler["KAYNAKLAR"] = kaynak_metni

        toplam_sure = time.perf_counter() - toplam_baslangic

        sure_notu = (
            "\n\n---\n"
            f"*Fotoğraf hazırlama: {foto_suresi:.1f} sn · "
            f"API yanıtı: {api_suresi:.1f} sn · "
            f"Toplam: {toplam_sure:.1f} sn · "
            f"Bulunan arama kaynağı: {len(kaynaklar)}*"
        )

        genel = bolumler.get(
            "GENEL_BAKIS",
            "Genel bakış bölümü oluşturulamadı."
        )
        genel += sure_notu

        sirali_anahtarlar = [
            "GENEL_BAKIS",
            "GORSEL_INCELEME",
            "TARIHCE",
            "KRONOLOJI",
            "MIMARI_SANAT",
            "ARKEOLOJI",
            "TARIHSEL_BAGLAM",
            "TURK_TARIHI",
            "KARSILASTIRMA",
            "KORUMA",
            "ONEM",
            "BELIRSIZLIKLAR",
            "KAYNAKLAR",
            "SONUC"
        ]

        sonuclar = [genel]

        for anahtar in sirali_anahtarlar[1:]:
            sonuclar.append(
                bolumler.get(
                    anahtar,
                    "Bu bölüm model tarafından ayrı bir başlık altında "
                    "oluşturulamadı. Genel Bakış sekmesindeki raporu "
                    "da inceleyebilirsin."
                )
            )

        sonuclar.append(
            f"İnceleme tamamlandı. Toplam süre: {toplam_sure:.1f} saniye."
        )

        return tuple(sonuclar)

    except Exception as hata:
        mesaj = (
            "## İnceleme sırasında hata oluştu\n\n"
            f"**Hata türü:** `{type(hata).__name__}`\n\n"
            f"**Ayrıntı:** `{str(hata)[:900]}`\n\n"
            "Render günlüklerinde hata ayrıntılarını kontrol et. "
            "Model adı, API anahtarı, kota veya Google Arama "
            "aracının desteklenmesiyle ilgili bir sorun olabilir."
        )

        return (mesaj,) + ("",) * 14


# =========================================================
# ARAYÜZ
# =========================================================

CSS = """
:root {
    --kirmizi: #e30a17;
    --koyu: #160d10;
    --altin: #d9b878;
}

body, .gradio-container {
    background: #160d10 !important;
    color: #fff8f5 !important;
}

.gradio-container {
    max-width: 1250px !important;
    margin: auto !important;
}

#hero {
    padding: 42px 22px;
    text-align: center;
    border: 1px solid #8f2730;
    border-radius: 20px;
    background:
        radial-gradient(
            circle at 50% 0%,
            rgba(227,10,23,.24),
            transparent 58%
        ),
        linear-gradient(140deg, #30151b, #160d10 65%, #271116);
    box-shadow: 0 12px 40px rgba(0,0,0,.25);
}

#hero h1 {
    color: #fff8f5;
    font-size: clamp(27px, 5vw, 46px);
    letter-spacing: 2px;
}

#hero .line {
    height: 2px;
    width: min(480px, 75%);
    margin: 22px auto;
    background: linear-gradient(
        90deg, transparent, #e30a17, #fff, #e30a17, transparent
    );
}

#hero .sub {
    color: #d9b878;
    letter-spacing: 2px;
    font-size: 12px;
}

.panel {
    border: 1px solid #573039;
    border-radius: 14px;
    padding: 14px;
    background: rgba(255,255,255,.025);
}

button.primary {
    background: linear-gradient(135deg, #e30a17, #a80612) !important;
    color: white !important;
    border: 1px solid #ff727a !important;
    font-weight: bold !important;
}

.tab-nav button.selected {
    border-color: #e30a17 !important;
}

#footer-note {
    text-align: center;
    color: #bca9aa;
    font-size: 12px;
    padding: 18px 8px;
    border-top: 1px solid #4b252b;
}
"""


with gr.Blocks(
    title="Tarihin İzini Sür | Kültür ve Miras",
    css=CSS,
    theme=gr.themes.Base(
        primary_hue="red",
        neutral_hue="slate"
    )
) as uygulama:

    gr.HTML("""
    <div style="
        position:fixed; top:14px; right:16px;
        z-index:99999; pointer-events:none;
    ">
        <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
            alt="Türk bayrağı"
            style="
                width:58px; height:auto;
                border:1px solid #d9b878;
                border-radius:4px;
                box-shadow:0 3px 14px rgba(0,0,0,.5);
            "
        >
    </div>
    """)

    gr.HTML("""
    <div id="hero">
        <div style="font-size:48px">🏛️</div>
        <h1>TARİHİN İZİNİ SÜR</h1>
        <div class="line"></div>
        <p>
            Bir fotoğrafın ardındaki tarihi keşfet.
            Kaynakları incele, geçmişi ayrıntılarıyla araştır.
        </p>
        <p class="sub">
            TARİH • ARKEOLOJİ • TÜRK KÜLTÜRÜ • MİRAS
        </p>
    </div>
    """)

    gr.Markdown(
        "## Yeni bir tarihî araştırma başlat\n"
        "Fotoğrafı yükle. Uygulama eseri tanımlamaya, tarihini "
        "araştırmaya ve kapsamlı bir rapor hazırlamaya çalışsın."
    )

    with gr.Group(elem_classes=["panel"]):
        fotograf = gr.Image(
            label="Tarihî eser fotoğrafı",
            type="filepath",
            height=340
        )

        baslat = gr.Button(
            "🇹🇷 AYRINTILI TARİHÎ ARAŞTIRMAYI BAŞLAT",
            variant="primary",
            size="lg"
        )

    durum = gr.Markdown("Fotoğraf yüklenmeye hazır.")

    with gr.Tabs():
        ciktilar = []

        for baslik in [
            "🏛️ Genel Bakış",
            "🔎 Görsel İnceleme",
            "📜 Ayrıntılı Tarihçe",
            "🗓️ Kronoloji",
            "🧱 Mimari ve Sanat",
            "⛏️ Arkeoloji",
            "🌍 Tarihsel Bağlam",
            "🇹🇷 Türk Tarihi",
            "⚖️ Karşılaştırma",
            "🏺 Koruma ve Miras",
            "⭐ Tarihsel Önem",
            "❔ Belirsizlikler",
            "📚 Kaynaklar",
            "📝 Genel Sonuç"
        ]:
            with gr.Tab(baslik):
                ciktilar.append(
                    gr.Markdown(
                        "Araştırmayı başlattığında bu bölüm "
                        "ayrıntılı bilgilerle doldurulacak."
                    )
                )

    gr.HTML("""
    <div id="footer-note">
        TARİHİN İZİNİ SÜR • Kültürel mirası tanı, araştır ve koru.
        <br>
        Yapay zekâ çıktıları hata içerebilir; önemli tarihsel
        iddiaları kaynaklardan ayrıca doğrula.
    </div>
    """)

    baslat.click(
        fn=eser_ara,
        inputs=[fotograf],
        outputs=ciktilar + [durum],
        show_progress="full"
    )


PORT = int(os.environ.get("PORT", "10000"))

uygulama.queue().launch(
    server_name="0.0.0.0",
    server_port=PORT
)
