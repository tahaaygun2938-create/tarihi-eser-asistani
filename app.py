
import os
import io
import json
import base64
import time
import re
import html

import gradio as gr
import requests
from PIL import Image


# API anahtarı sadece Render ortam değişkenlerinden okunur.
# Uygulamada kullanıcıya API anahtarı kutusu gösterilmez.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.8-flash"


def gemini_istegi(govde):
    """Gemini API isteğini geçici hatalarda tekrar dener."""

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Sunucu yapılandırması eksik. Render'da "
            "GEMINI_API_KEY ortam değişkeni tanımlanmalı."
        )

    adres = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    son_hata = "Bilinmeyen API hatası."

    for deneme in range(4):
        try:
            cevap = requests.post(
                adres,
                headers={"x-goog-api-key": GEMINI_API_KEY},
                json=govde,
                timeout=120
            )

            if cevap.status_code == 200:
                return cevap.json()

            son_hata = (
                f"Gemini HTTP {cevap.status_code}: "
                f"{cevap.text[:500]}"
            )

            if cevap.status_code not in (429, 500, 502, 503, 504):
                break

        except requests.RequestException as hata:
            son_hata = f"Bağlantı hatası: {hata}"

        if deneme < 3:
            time.sleep(2 ** (deneme + 1))

    raise RuntimeError(son_hata)


def markdown_guvenli(deger):
    """Modelin döndürdüğü alanları metne dönüştürür."""
    if deger is None:
        return "Bu konuda yeterli bilgi elde edilemedi."

    if isinstance(deger, list):
        return "\n".join(f"- {str(x)}" for x in deger)

    if isinstance(deger, dict):
        return "\n".join(
            f"- **{anahtar}:** {deger}"
            for anahtar, deger in deger.items()
        )

    return str(deger)


def eser_ara(fotograf_yolu):
    """Tarihî eser fotoğrafını inceler ve ayrıntılı araştırma hazırlar."""

    if not GEMINI_API_KEY:
        return (
            "## Sunucu yapılandırması eksik\n\n"
            "Uygulama yöneticisinin Render ortam değişkenlerine "
            "`GEMINI_API_KEY` eklemesi gerekiyor.",
            "", "", "", "", "", ""
        )

    if not fotograf_yolu:
        return (
            "Lütfen önce bir eser fotoğrafı yükle.",
            "", "", "", "", "", ""
        )

    try:
        # Görseli API için uygun boyuta getir.
        with Image.open(fotograf_yolu) as resim:
            resim = resim.convert("RGB")
            resim.thumbnail((1400, 1400))

            tampon = io.BytesIO()
            resim.save(
                tampon,
                format="JPEG",
                quality=88,
                optimize=True
            )
            foto_bytes = tampon.getvalue()

        foto_base64 = base64.b64encode(
            foto_bytes
        ).decode("utf-8")

        prompt = """
Sen arkeoloji, sanat tarihi, mimarlık tarihi ve Türk tarihi
konularında çalışan titiz bir araştırma uzmanısın.

Gönderilen fotoğrafı ayrıntılı incele. Görseldeki eseri
tanımlamaya çalış ve kapsamlı bir Türkçe araştırma dosyası hazırla.

YALNIZCA geçerli bir JSON nesnesi döndür.
Markdown kod çiti kullanma.
Belirtilen tüm alanlar metin olmalı.

JSON alanları:

{
  "eser_adi": "Eserin olası adı ve alternatif tanımlamalar",
  "guven": "Güven düzeyi ve gerekçesi",
  "genel_bakis": "Eserin ayrıntılı tanıtımı, genel görünümü,
  boyutu biliniyorsa boyutu, türü ve ayırt edici özellikleri",
  "gorsel_inceleme": "Fotoğrafta gerçekten görülebilen şekiller,
  figürler, yazılar, motifler, malzemeler ve fiziksel ayrıntılar",
  "tarihce": "Olası yapım tarihi, dönem, uygarlık, tarihsel
  koşullar, siyasi ortam ve dönemin önemli gelişmeleri",
  "kronoloji": "Eserin ortaya çıktığı dönemden sonraki tarihsel
  aşamalarına kadar kronolojik anlatım; bilinmeyen tarihleri
  kesinmiş gibi yazma",
  "mimari_ve_sanat": "Mimari tarz, plan, teknik, sanat üslubu,
  süsleme, ikonografi ve benzer eserlerle karşılaştırma",
  "arkeoloji": "Arkeolojik bağlam, kazı ve buluntu bilgileri
  biliniyorsa bunlar; bilinmiyorsa hangi bilgilerin eksik olduğu",
  "kullanim_ve_islev": "Eserin olası ilk işlevi, kullanım amacı,
  toplumsal veya dinî rolü ve sonraki kullanım değişiklikleri",
  "tarihsel_baglam": "Eserin dönemindeki devletler, toplum,
  ekonomi, ticaret, din, kültür ve önemli tarihsel olaylarla ilişkisi",
  "turk_tarihi": "Türk tarihiyle doğrulanabilir bir ilişkisi varsa
  açıkla. İlişki yoksa veya kanıt yetersizse bunu açıkça belirt.
  Sırf Türk temalı bir uygulamada bulunduğu için eseri Türk eseri
  olarak tanımlama",
  "karsilastirma": "Benzer eserler, ortak özellikler ve önemli
  farklılıklar. Kesin olmayan benzetmeleri belirt",
  "korunma": "Biliniyorsa günümüzdeki durumu, restorasyon,
  koruma sorunları ve kültürel miras değeri",
  "onem": "Sanat, tarih, arkeoloji, kültür ve insanlık tarihi
  açısından önemi",
  "belirsizlikler": "Alternatif kimlikler, eksik kanıtlar,
  fotoğraftan anlaşılamayan noktalar ve olası yanlış tanımlamalar",
  "kaynak_onerileri": "Araştırmayı doğrulamak için kullanılabilecek
  resmî kurumlar, müzeler, kataloglar, akademik yayın türleri ve
  aranabilecek konu başlıkları"
}

ARAŞTIRMA KURALLARI:

1. Türkçe ve ayrıntılı yaz. Her bölüme mümkün olduğunca anlamlı
   tarihsel bilgi ekle; gereksiz tekrar yapma.
2. Fotoğrafta görülenleri, tarihsel bilgileri ve varsayımları
   birbirinden açıkça ayır.
3. Fotoğraftan tek başına kesin kimlik, konum veya tarih
   belirlenemiyorsa bunu söyle.
4. Eserin adı konusunda emin değilsen alternatifleri açıkla.
5. Görünmeyen yazıları okuduğunu iddia etme; yazıtları uydurma.
6. Kazı raporu, buluntu yeri, restorasyon tarihi, müze numarası,
   kaynakça veya internet bağlantısı uydurma.
7. Kaynak önerilerini doğrulanmış kaynak gibi sunma.
8. Eserin tarihini anlatırken dönemin önemli siyasi ve kültürel
   gelişmelerini de açıkla; fakat eserle bağlantısı bilinmiyorsa
   doğrudan bağlantı kurma.
9. Türk tarihi bölümünde Anadolu Türk tarihi, Selçuklular,
   Osmanlılar, Türkiye Cumhuriyeti veya diğer Türk topluluklarıyla
   ilişkileri yalnızca tarihsel kanıt bulunduğunda anlat.
10. Bir eserin Türk, Bizans, Roma, Yunan, Pers veya başka bir
    kültüre ait olduğunu yalnızca görünüşüne dayanarak kesinleştirme.
11. Her bölümde bilgi düzeyini dürüstçe belirt.
12. Herhangi bir alan için bilgi yoksa bunu açıkça yaz.
"""

        govde = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": foto_base64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.25,
                "responseMimeType": "application/json",
                "maxOutputTokens": 10000
            }
        }

        sonuc = gemini_istegi(govde)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            return (
                "## Yanıt alınamadı\n\n"
                "Model yanıt üretmedi. Farklı bir fotoğrafla "
                "tekrar deneyebilirsin.",
                "", "", "", "", "", ""
            )

        parcalar = adaylar[0].get(
            "content", {}
        ).get("parts", [])

        metin = "".join(
            parca.get("text", "")
            for parca in parcalar
        ).strip()

        metin = re.sub(
            r"^\s*```(?:json)?\s*|\s*```\s*$",
            "",
            metin,
            flags=re.IGNORECASE
        ).strip()

        bilgi = json.loads(metin)

        def alan(ad, varsayilan="Yeterli bilgi elde edilemedi."):
            return markdown_guvenli(
                bilgi.get(ad, varsayilan)
            )

        eser_adi = html.escape(
            str(bilgi.get("eser_adi", "Olası Tarihî Eser"))
        )
        guven = markdown_guvenli(
            bilgi.get("guven", "Belirlenemedi.")
        )

        genel = f"""
# 🏛️ {eser_adi}

**Güven düzeyi:** {guven}

---

## Eserin Tanıtımı

{alan("genel_bakis")}

## Görsel İnceleme

{alan("gorsel_inceleme")}

## Tarihsel ve Kültürel Önemi

{alan("onem")}

## Tarihsel Bağlam

{alan("tarihsel_baglam")}
"""

        tarihce = f"""
# 📜 Ayrıntılı Tarihçe

## Tarihsel Gelişim

{alan("tarihce")}

## Kronolojik Süreç

{alan("kronoloji")}

## Kullanım Amacı ve İşlevi

{alan("kullanim_ve_islev")}

## Eserin Ortaya Çıktığı Dönem

Eserin tarihini değerlendirirken dönemin siyasi, toplumsal
ve kültürel koşullarını birbirinden ayırmak önemlidir.

{alan("tarihsel_baglam")}
"""

        mimari = f"""
# 🧱 Mimari ve Sanatsal İnceleme

## Mimari Özellikler ve Sanat Üslubu

{alan("mimari_ve_sanat")}

## Arkeolojik Bulgular

{alan("arkeoloji")}

## Görsel Kanıtlar

{alan("gorsel_inceleme")}

## Benzer Eserlerle Karşılaştırma

{alan("karsilastirma")}
"""

        turk_tarihi = f"""
# 🇹🇷 Türk Tarihi ve Kültürel Bağlam

{alan("turk_tarihi")}

## Dönemin Kültürel Çevresi

{alan("tarihsel_baglam")}

## Önemli Not

Türk tarihiyle ilişki, yalnızca bayrak, motif veya görünüş
benzerliğine dayanarak kurulamaz. Tarih, coğrafya ve
güvenilir kanıtlar birlikte değerlendirilmelidir.
"""

        koruma = f"""
# 🏺 Koruma ve Kültürel Miras

## Günümüzdeki Durum

{alan("korunma")}

## Kültürel Miras Değeri

{alan("onem")}

## Belirsizlikler ve Alternatif Tanımlamalar

{alan("belirsizlikler")}
"""

        karsilastirma = f"""
# 🔍 Karşılaştırmalı Değerlendirme

## Benzer Eserler

{alan("karsilastirma")}

## Tanımlama Güveni

{guven}

## Açık Kalan Sorular

{alan("belirsizlikler")}
"""

        kaynaklar = f"""
# 📚 Kaynak ve Doğrulama Rehberi

## Önerilen Araştırma Yolları

{alan("kaynak_onerileri")}

## Başvurulabilecek Kurumlar

- [T.C. Kültür ve Turizm Bakanlığı](https://www.ktb.gov.tr/)
- [Türkiye Kültür Portalı](https://www.kulturportali.gov.tr/)
- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [DergiPark Akademik Yayınları](https://dergipark.org.tr/)

Bu bağlantılar araştırma başlangıç noktalarıdır; eser hakkındaki
belirli bir bilginin bu kaynaklarda doğrulandığı anlamına gelmez.
Eserin adı, tarihi, buluntu yeri ve kaynakları ayrıca kontrol edilmelidir.
"""

        return (
            genel,
            tarihce,
            mimari,
            turk_tarihi,
            koruma,
            karsilastirma,
            kaynaklar
        )

    except json.JSONDecodeError:
        return (
            "## Yanıt biçimi okunamadı\n\n"
            "Model geçerli bir araştırma dosyası döndürmedi. "
            "Lütfen yeniden dene.",
            "", "", "", "", "", ""
        )

    except Exception as hata:
        hata_metni = str(hata)[:500]
        return (
            "## Analiz sırasında hata oluştu\n\n"
            f"`{type(hata).__name__}: {hata_metni}`\n\n"
            "Sorun sürerse Render Logs bölümünü kontrol et.",
            "", "", "", "", "", ""
        )


# ---------------- TÜRK TEMALI TASARIM ----------------

css = """
:root {
    --kirmizi: #e30a17;
    --koyu: #160d10;
    --panel: #24171a;
    --altin: #d9b878;
    --beyaz: #fff8f5;
}

body, .gradio-container {
    background: var(--koyu) !important;
    color: var(--beyaz) !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}

#hero {
    position: relative;
    overflow: hidden;
    padding: 45px 22px 36px;
    text-align: center;
    border: 1px solid #8f2730;
    border-radius: 20px;
    background:
        radial-gradient(
            circle at 50% 0%,
            rgba(227,10,23,.23),
            transparent 55%
        ),
        linear-gradient(140deg, #30151b, #160d10 65%, #271116);
    box-shadow: 0 12px 40px rgba(0,0,0,.25);
}

#hero h1 {
    color: #fff8f5;
    font-size: clamp(28px, 5vw, 48px);
    letter-spacing: 2px;
    margin-bottom: 10px;
}

#hero .alt-baslik {
    color: var(--altin);
    letter-spacing: 3px;
    font-size: 12px;
}

#hero .cizgi {
    height: 2px;
    width: min(480px, 75%);
    margin: 22px auto;
    background: linear-gradient(
        90deg, transparent, var(--kirmizi), #fff, var(--kirmizi), transparent
    );
}

#hero .aciklama {
    color: #e7d9d9;
    line-height: 1.8;
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

button.primary:hover {
    filter: brightness(1.12);
}

.tab-nav button.selected {
    border-color: var(--kirmizi) !important;
    color: #fff !important;
}

footer {
    display: none !important;
}

#footer-note {
    text-align: center;
    color: #bca9aa;
    font-size: 12px;
    padding: 18px 8px;
    border-top: 1px solid #4b252b;
}

@media (max-width: 600px) {
    #hero {
        padding: 68px 14px 28px;
    }

    #hero .alt-baslik {
        letter-spacing: 1px;
    }
}
"""


with gr.Blocks(
    title="Tarihî Eser Asistanı | Kültür ve Miras",
    css=css,
    theme=gr.themes.Base(
        primary_hue="red",
        neutral_hue="slate"
    )
) as uygulama:

    # Sağ üstte Türk bayrağı
    gr.HTML("""
    <div style="
        position:fixed;
        top:16px;
        right:20px;
        z-index:99999;
        pointer-events:none;
    ">
        <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
            alt="Türk Bayrağı"
            style="
                display:block;
                width:62px;
                height:auto;
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
        <div class="cizgi"></div>
        <p class="aciklama">
            Bir fotoğraftan yola çık, geçmişin izlerini araştır.
            <br>
            Arkeoloji, mimarlık, uygarlıklar ve kültürel miras.
        </p>
        <p class="alt-baslik">
            TARİH • ARKEOLOJİ • TÜRK KÜLTÜRÜ • MİRAS
        </p>
    </div>
    """)

    gr.Markdown(
        "## Yeni bir keşfe hazır mısın?\n"
        "Bir eser fotoğrafı yükle; ayrıntılı araştırma dosyanı oluştur."
    )

    with gr.Group(elem_classes=["panel"]):
        fotograf_girdisi = gr.Image(
            label="Tarihî eser fotoğrafı",
            type="filepath",
            height=350
        )

        arastir_butonu = gr.Button(
            "🇹🇷  TARİHÎ İNCELEMEYİ BAŞLAT",
            variant="primary",
            size="lg"
        )

    gr.Markdown(
        "## Araştırma Dosyası\n"
        "Sonuçları aşağıdaki bölümlerden inceleyebilirsin."
    )

    with gr.Tabs():
        with gr.Tab("🏛️ Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Fotoğraf yükle ve incelemeyi başlat."
            )

        with gr.Tab("📜 Tarihçe"):
            tarihce_cikti = gr.Markdown(
                "Eserin dönemi ve tarihsel gelişimi burada gösterilecek."
            )

        with gr.Tab("🧱 Mimari ve Arkeoloji"):
            mimari_cikti = gr.Markdown(
                "Mimari, sanat üslubu ve arkeolojik ayrıntılar burada."
            )

        with gr.Tab("🇹🇷 Türk Tarihi"):
            turk_cikti = gr.Markdown(
                "Eserin Türk tarihiyle ilişkisi kanıtlara göre incelenecek."
            )

        with gr.Tab("🏺 Koruma ve Miras"):
            koruma_cikti = gr.Markdown(
                "Korunma durumu ve kültürel miras değeri burada."
            )

        with gr.Tab("🔍 Karşılaştırma"):
            karsilastirma_cikti = gr.Markdown(
                "Benzer eserler ve belirsizlikler burada."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Doğrulama yolları ve araştırma kurumları burada."
            )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[fotograf_girdisi],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            mimari_cikti,
            turk_cikti,
            koruma_cikti,
            karsilastirma_cikti,
            kaynak_cikti
        ],
        show_progress="full"
    )

    gr.HTML("""
    <div id="footer-note">
        TARİHİN İZİNİ SÜR • Kültürel mirası tanı, araştır ve koru.
        <br>
        Yapay zekâ tarafından üretilen bilgiler akademik kaynaklarla
        doğrulanmalıdır.
    </div>
    """)


PORT = int(os.environ.get("PORT", "10000"))

uygulama.queue().launch(
    server_name="0.0.0.0",
    server_port=PORT
)
