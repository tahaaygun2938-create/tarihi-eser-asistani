
import os
import io
import re
import time
import html
import base64
import requests
import gradio as gr
from PIL import Image


# =====================================================
# AYARLAR
# =====================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

MAX_OUTPUT_TOKENS = 12000
IMAGE_MAX_SIZE = (1200, 1200)
IMAGE_QUALITY = 82


# =====================================================
# KAPSAMLI TARİH ARAŞTIRMASI PROMPT'U
# =====================================================

PROMPT = r"""
Sen tarih, arkeoloji, sanat tarihi, mimarlık tarihi ve kültürel
miras alanlarında çalışan dikkatli bir araştırma asistanısın.

Görevin, kullanıcının yüklediği fotoğraftaki eseri tanımlamak,
hakkında güvenilir kaynaklardan araştırma yapmak ve kapsamlı,
uzun, ayrıntılı bir Türkçe araştırma raporu hazırlamaktır.

Google Arama aracını kullanarak eserin kimliğini ve tarihini
güvenilir kaynaklardan araştır. Öncelikle müze kataloglarını,
resmî kurumları, üniversiteleri, akademik yayınları, kazı
raporlarını ve UNESCO gibi kurumların kayıtlarını tercih et.

TEMEL KURALLAR:
- Fotoğrafta gerçekten görülen ayrıntılarla tarihsel bilgileri ayır.
- Kimlik kesin değilse alternatifleri ve gerekçelerini açıkla.
- Bilinmeyen bilgileri uydurma.
- Sahte kazı raporu, envanter numarası, alıntı veya kaynak üretme.
- Kaynakların desteklemediği iddiaları kesin gerçek gibi sunma.
- Türk tarihiyle ilgisi kanıtlanmıyorsa zorla bağlantı kurma.
- Bilinmeyen bilgileri açıkça belirt.
- Eserin tarihini yalnızca fotoğrafın görünümünden kesinleştirme.
- Uzunluğu tekrar ederek değil, yeni bilgilerle artır.
- Önemli iddiaları mümkün olduğunda [1], [2] gibi kaynak
  numaralarıyla ilişkilendir.
- Raporun sonunda kaynak numaralarını eşleştiren kaynakça ver.
- Gerçekten açılmayan veya bulunmayan bir kaynağı kullanılmış
  gibi gösterme.
- Yanıt Türkçe olmalı.

Aşağıdaki bölüm işaretlerini aynen kullan. Her bölümü ayrı ayrı
ve kapsamlı biçimde yaz. Kısa bir özetle yetinme.

[[GENEL_BAKIS]]

# 1. Eserin tanımlanması
Eserin olası adı, alternatif isimleri, türü, ait olduğu uygarlık,
muhtemel yapım dönemi ve bu tarihlendirmenin gerekçesi.
Tanımlama güven düzeyi, benzer eserlerle karıştırılma ihtimali,
fotoğraftan belirlenebilen ve belirlenemeyen özellikler.

[[GORSEL_INCELEME]]

# 2. Görsel inceleme
Görülebilen biçimler, malzemeler, yüzeyler, motifler, figürler,
semboller, süslemeler, yazılar, aşınma izleri ve fiziksel ayrıntılar.
Fotoğrafın açı, ışık ve çözünürlük bakımından sınırları.
Gözlem ile yorum arasındaki fark.

[[TARIHCE]]

# 3. Ayrıntılı tarihçe
Eserin ortaya çıktığı tarihsel ortamı uzun ve kronolojik biçimde anlat.
Yapılış amacı, yapım süreci, dönemin siyasi ve toplumsal koşulları,
eserle ilişkili kişiler, kullanım amacı, zaman içindeki değişimler,
terk edilmesi, yeniden keşfedilmesi, kazılar, restorasyonlar ve
günümüze ulaşma sürecini araştır.

Her tarihsel aşamayı ayrı alt başlıklarla açıkla.
Doğrulanamayan tarih veya olayları uydurma.

[[KRONOLOJI]]

# 4. Ayrıntılı kronoloji
Eserin yapım dönemi, uygarlığın önemli gelişmeleri, tarihsel dönüm
noktaları, keşif, kazı, restorasyon ve müzeye alınma tarihleri.
Mümkün olduğunda tarih, olay ve açıklama sütunları olan bir tablo
hazırla. Yaklaşık tarihleri yaklaşık olarak işaretle.

[[MIMARI_SANAT]]

# 5. Mimari ve sanat tarihi
Mimari plan, biçim, oran, kompozisyon, yapım teknikleri,
malzemeler, süslemeler, motifler, sembolizm, sanat üslubu,
bölgesel etkiler, benzer eserler, sanatçı veya atölye hakkında
bilinenler ve eserin sonraki dönemlere etkisi.

[[ARKEOLOJI]]

# 6. Arkeolojik inceleme
Biliniyorsa buluntu yeri, kazı geçmişi, kazı ekipleri, arkeolojik
bağlam, tarihlendirme yöntemleri, buluntular, envanter numarası,
katalog bilgileri, benzer buluntular ve bilimsel tartışmalar.
Yalnızca kaynaklarla desteklenen bilgileri aktar.

[[TARIHSEL_BAGLAM]]

# 7. Dönemin tarihsel bağlamı
Siyasi yapı, yönetim biçimi, toplum, günlük yaşam, ekonomi,
ticaret, din, inanç, askerî yapı, bölgesel ilişkiler, dil,
yazı, eğitim ve kültürel yaşam.
Genel dönem bilgisini eser hakkında doğrudan kanıt gibi sunma.

[[TURK_TARIHI]]

# 8. Türk tarihiyle ilişkisi
Varsa Türk devletleri, toplulukları, Selçuklu, Osmanlı, Anadolu
beylikleri veya diğer tarihî dönemlerle ilişkisini açıkla.
Türklerin bölgeye gelişi, kültürel dönüşüm, mimari ve sanat
etkilerini kaynaklarla değerlendir.
Doğrudan ilişki kanıtlanamıyorsa bunu dürüstçe belirt.

[[KARSILASTIRMA]]

# 9. Karşılaştırmalı eser analizi
Güvenilir kaynaklarla belirlenebiliyorsa en az üç benzer eseri
karşılaştır. Tarih, konum, malzeme, üslup, ortak özellikler,
farklılıklar ve tarihsel anlamlarını açıkla.
Benzer eserleri veya tarihleri uydurma.

[[KORUMA]]

# 10. Koruma ve kültürel miras
Güncel konum, korunma durumu, restorasyonlar, riskler, resmî
tescil veya miras statüsü, doğal ve insan kaynaklı etkiler,
koruma çalışmaları ve tartışmalar.
Güncel durumu doğrulayacak kaynak bulunamazsa bunu belirt.

[[ONEM]]

# 11. Tarihsel önem
Eserin tarihçiler, arkeologlar, sanat tarihçileri ve mimarlık
tarihi açısından önemi. Bölgesel ve evrensel kültür mirasındaki
yeri, günümüzdeki anlamı ve geçmiş hakkında sağlayabildiği bilgiler.

[[BELIRSIZLIKLAR]]

# 12. Tartışmalar ve belirsizlikler
Kimlik, tarihlendirme ve yorum farklılıkları; kaynaklar arasındaki
uyuşmazlıklar; fotoğraftan belirlenemeyen noktalar ve kesin sonuca
ulaşmak için gereken ek kanıtlar.

[[KAYNAKLAR]]

# 13. Kaynakça
Araştırma sırasında gerçekten bulunan kaynakların başlığı,
yazarı veya kurumu, doğrudan bağlantısı ve desteklediği iddia.
Akademik yayınlar, müze katalogları, resmî kurumlar ve kazı
raporlarını tercih et. Kaynak önerilerini kullanılmış kaynaklardan
ayrı tut. Sahte kaynak veya URL üretme.

[[SONUC]]

# 14. Genel değerlendirme
Eserin kimliğine dair en güçlü sonuç, en sağlam tarihsel çıkarımlar,
güven düzeyi, araştırmanın önemli bulguları ve kesinleştirilemeyen
sorular. Daha iyi teşhis için gerekli ek fotoğraf ve bilgiler.

SON TALİMAT:
Her bölümü kapsamlı ve ayrıntılı yaz. Gerektiğinde alt başlıklar,
tablolar ve madde listeleri kullan. Aynı bilgiyi tekrarlayarak
uzatma; her bölüm yeni ve anlamlı bilgi içersin.
"""


# =====================================================
# GEMINI API İSTEĞİ
# =====================================================

def gemini_istegi(govde):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadı. Render Environment "
            "bölümüne API anahtarını eklemelisin."
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

            if cevap.status_code not in (
                408, 429, 500, 502, 503, 504
            ):
                break

        except requests.RequestException as hata:
            son_hata = f"Bağlantı hatası: {hata}"

        if deneme < 2:
            time.sleep(2 ** (deneme + 1))

    raise RuntimeError(son_hata)


# =====================================================
# FOTOĞRAF HAZIRLAMA
# =====================================================

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


# =====================================================
# ARAMA KAYNAKLARINI TOPLAMA
# =====================================================

def kaynaklari_al(cevap):
    kaynaklar = []
    gorulen = set()

    for aday in cevap.get("candidates", []):
        meta = aday.get("groundingMetadata", {}) or {}

        for parca in meta.get("groundingChunks", []) or []:
            web_bilgisi = parca.get("web", {}) or {}
            url = web_bilgisi.get("uri", "")
            baslik = web_bilgisi.get("title", "Kaynak")

            if url.startswith(("https://", "http://")):
                if url not in gorulen:
                    gorulen.add(url)
                    kaynaklar.append((baslik, url))

    return kaynaklar


def kaynak_metni_olustur(kaynaklar):
    if not kaynaklar:
        return """
Arama kaynakları API yanıtında bulunamadı. Aşağıdaki bağlantılar
genel araştırma başlangıç noktalarıdır; esere dair doğrulanmış
kaynaklar olarak değerlendirilmemelidir.

- [Kültür ve Turizm Bakanlığı](https://www.ktb.gov.tr/)
- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [DergiPark](https://dergipark.org.tr/)
"""

    satirlar = [
        "Araştırma sırasında API tarafından döndürülen bağlantılar:"
    ]

    for sira, (baslik, url) in enumerate(kaynaklar, 1):
        baslik = html.escape(baslik)
        url_guvenli = html.escape(url, quote=True)
        satirlar.append(
            f"{sira}. [{baslik}]({url_guvenli})"
        )

    satirlar.append(
        "\nNot: Kaynak bağlantılarının bulunması, her iddiayı "
        "doğruladıkları anlamına gelmez. İlgili sayfaları kontrol et."
    )

    return "\n\n".join(satirlar)


# =====================================================
# RAPOR BÖLÜMLERİNİ AYIRMA
# =====================================================

BOLUM_SIRASI = [
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


# =====================================================
# ANA ARAŞTIRMA FONKSİYONU
# =====================================================

def eser_ara(fotograf_yolu):
    toplam_baslangic = time.perf_counter()

    if not GEMINI_API_KEY:
        hata = (
            "## API anahtarı eksik\n\n"
            "Render → Environment bölümüne `GEMINI_API_KEY` "
            "değişkenini ekle. API anahtarını GitHub'a koyma."
        )
        return (hata,) + ("",) * 14

    if not fotograf_yolu:
        return (
            "Lütfen önce bir eser fotoğrafı yükle.",
        ) + ("",) * 14

    try:
        # Fotoğrafı hazırla.
        foto_baslangic = time.perf_counter()
        foto_base64 = fotograf_hazirla(fotograf_yolu)
        foto_suresi = time.perf_counter() - foto_baslangic

        # Uzun araştırma isteğini oluştur.
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

        # Model yanıtını al.
        api_baslangic = time.perf_counter()
        cevap = gemini_istegi(govde)
        api_suresi = time.perf_counter() - api_baslangic

        adaylar = cevap.get("candidates", [])

        if not adaylar:
            raise RuntimeError(
                "Model yanıt üretmedi. API geri bildirimi: "
                + str(cevap.get("promptFeedback", {}))[:500]
            )

        parcalar = adaylar[0].get(
            "content", {}
        ).get("parts", [])

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

        # Bölümlere ayır.
        bolumler = raporu_bol(rapor)

        if len(bolumler) < 4:
            bolumler["GENEL_BAKIS"] = rapor

        # Gerçek arama metaverisinde bulunan kaynakları ekle.
        kaynaklar = kaynaklari_al(cevap)
        kaynak_ek = kaynak_metni_olustur(kaynaklar)

        if bolumler.get("KAYNAKLAR"):
            bolumler["KAYNAKLAR"] += "\n\n---\n\n" + kaynak_ek
        else:
            bolumler["KAYNAKLAR"] = kaynak_ek

        toplam_sure = time.perf_counter() - toplam_baslangic

        sure_notu = (
            "\n\n---\n"
            f"*Fotoğraf hazırlama: {foto_suresi:.1f} sn · "
            f"API yanıtı: {api_suresi:.1f} sn · "
            f"Toplam: {toplam_sure:.1f} sn · "
            f"Bulunan arama bağlantısı: {len(kaynaklar)}*"
        )

        genel = bolumler.get(
            "GENEL_BAKIS",
            "Genel bakış bölümü oluşturulamadı."
        ) + sure_notu

        sonuclar = [genel]

        for anahtar, _baslik in BOLUM_SIRASI[1:]:
            sonuclar.append(
                bolumler.get(
                    anahtar,
                    "Bu bölüm ayrı bir başlık altında oluşturulamadı. "
                    "Genel Bakış sekmesindeki raporu da inceleyebilirsin."
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
            "Model adını, API anahtarını, kotayı ve Render "
            "günlüklerini kontrol et."
        )

        return (mesaj,) + ("",) * 14


# =====================================================
# TASARIM
# =====================================================

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


# =====================================================
# GRADIO ARAYÜZÜ
# =====================================================

with gr.Blocks(
    title="Tarihin İzini Sür | Kültür ve Miras",
    css=CSS,
    theme=gr.themes.Base(
        primary_hue="red",
        neutral_hue="slate"
    )
) as uygulama:

    # Türk bayrağı ve imza
    gr.HTML("""
    <div style="
        position:fixed;
        top:14px;
        right:16px;
        z-index:99999;
        pointer-events:none;
        text-align:center;
    ">
        <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
            alt="Türk bayrağı"
            style="
                display:block;
                width:58px;
                height:auto;
                border:1px solid #d9b878;
                border-radius:4px;
                box-shadow:0 3px 14px rgba(0,0,0,.5);
            "
        >

        <div style="
            margin-top:6px;
            color:#d9b878;
            font-size:10px;
            font-family:Georgia,serif;
            letter-spacing:1px;
            white-space:nowrap;
            text-shadow:0 1px 5px #000;
        ">
            by Taha Anıl Aygün
        </div>
    </div>
    """)

    gr.HTML("""
    <div id="hero">
        <div style="font-size:48px">🏛️</div>
        <h1>TARİHİN İZİNİ SÜR</h1>
        <div class="line"></div>
        <p>
            Bir fotoğrafın ardındaki tarihi keşfet.
            Geçmişi araştır, kaynakları incele.
        </p>
        <p class="sub">
            TARİH • ARKEOLOJİ • TÜRK KÜLTÜRÜ • MİRAS
        </p>
    </div>
    """)

    gr.Markdown(
        "## Yeni bir tarihî araştırma başlat\n"
        "Bir eser fotoğrafı yükle. Ayrıntılı tarihçe, kronoloji, "
        "arkeolojik değerlendirme ve kaynak araştırması oluştur."
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

        sekmeler = [
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
        ]

        for baslik in sekmeler:
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
        Yapay zekâ tarafından oluşturulan bilgiler doğrulanmalıdır.
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
