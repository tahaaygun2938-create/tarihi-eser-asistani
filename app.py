
import os
import io
import json
import base64
import time
import re

import gradio as gr
import requests
from PIL import Image


# Render ortam değişkenlerinden API anahtarını al.
GLOBAL_ANAHTAR = os.environ.get("GEMINI_API_KEY", "")


def gemini_istegi(govde, api_key):
    """Gemini API isteğini yapar ve geçici hatalarda tekrar dener."""

    model = "gemini-3.8-flash"
    adres = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    son_hata = None

    for deneme in range(4):
        try:
            cevap = requests.post(
                adres,
                headers={"x-goog-api-key": api_key},
                json=govde,
                timeout=90
            )

            if cevap.status_code == 200:
                return cevap.json()

            son_hata = (
                f"Gemini HTTP {cevap.status_code}: "
                f"{cevap.text[:700]}"
            )

            if cevap.status_code not in [429, 500, 502, 503, 504]:
                break

        except requests.RequestException as hata:
            son_hata = f"Bağlantı hatası: {hata}"

        if deneme < 3:
            time.sleep(2 ** (deneme + 1))

    raise RuntimeError(
        son_hata or "Gemini isteği tamamlanamadı."
    )


def eser_ara(fotograf_yolu, kullanici_anahtari):
    """Fotoğrafı analiz eder ve dört bölümde sonuç döndürür."""

    api_key = (
        kullanici_anahtari.strip()
        if kullanici_anahtari and kullanici_anahtari.strip()
        else GLOBAL_ANAHTAR
    )

    if not api_key:
        mesaj = (
            "### API anahtarı bulunamadı\n\n"
            "Gemini API anahtarını yukarıdaki alana gir "
            "ve yeniden dene."
        )
        return mesaj, "", "", ""

    if not fotograf_yolu:
        return (
            "Lütfen önce bir eser fotoğrafı yükle.",
            "",
            "",
            ""
        )

    try:
        # Fotoğrafı küçült ve JPEG'e dönüştür.
        with Image.open(fotograf_yolu) as resim:
            resim = resim.convert("RGB")
            resim.thumbnail((1200, 1200))

            tampon = io.BytesIO()
            resim.save(
                tampon,
                format="JPEG",
                quality=85,
                optimize=True
            )
            foto_bytes = tampon.getvalue()

        foto_base64 = base64.b64encode(
            foto_bytes
        ).decode("utf-8")

        prompt = """
Sen tarihî eserler, arkeoloji ve sanat tarihi konusunda
dikkatli bir araştırma asistanısın.

Gönderilen fotoğrafı incele ve yalnızca geçerli bir JSON
nesnesi döndür. Markdown kod çiti ekleme.

Şu alanları oluştur:

{
  "eser_adi": "Eserin veya yapının olası adı",
  "guven": "Düşük, Orta veya Yüksek; gerekçesiyle birlikte",
  "genel_bakis": "Eserin görünümü, mimarisi ve tanıtımı",
  "tarihce": "Olası dönem, uygarlık ve tarihsel bağlam",
  "arkeolojik_bulgular": "Görülebilen yapı özellikleri,
  malzemeler, figürler ve süslemeler",
  "tarihsel_onem": "Kültürel, sanatsal ve tarihsel önem",
  "belirsizlikler": "Alternatif olasılıklar ve bilinmeyenler"
}

Kurallar:
- Türkçe yaz ve her bölümü açıklayıcı biçimde doldur.
- Tahminleri kesin bilgi gibi sunma.
- Fotoğrafta görünmeyen ayrıntıları uydurma.
- Konum kesin değilse bunu açıkça belirt.
- Yalnızca fotoğraftan kesin tarih veya kimlik
  belirlenemeyebileceğini açıkla.
- Eserin adını belirlerken görsel kanıtlara dayan.
- Bilmediğin bilgileri açıkça belirt.
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
                "temperature": 0.35,
                "responseMimeType": "application/json"
            }
        }

        sonuc = gemini_istegi(govde, api_key)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            return (
                "Yapay zekâ yanıt üretemedi. "
                "Farklı bir fotoğraf deneyebilirsin.",
                "",
                "",
                ""
            )

        parcalar = adaylar[0].get(
            "content", {}
        ).get("parts", [])

        metin = "".join(
            parca.get("text", "")
            for parca in parcalar
        ).strip()

        if not metin:
            return (
                "Gemini boş yanıt verdi. Lütfen tekrar dene.",
                "",
                "",
                ""
            )

        # Olası Markdown kod çitlerini temizle.
        metin_temiz = re.sub(
            r"^\s*```(?:json)?\s*|\s*```\s*$",
            "",
            metin,
            flags=re.IGNORECASE
        ).strip()

        try:
            bilgi = json.loads(metin_temiz)
        except json.JSONDecodeError:
            return (
                "## Araştırma Dosyası\n\n" + metin_temiz,
                "Yanıt JSON biçiminde çözümlenemedi.",
                "Ayrı bulgu bölümü oluşturulamadı.",
                "Kaynaklar ayrıca doğrulanmalıdır."
            )

        eser_adi = str(
            bilgi.get("eser_adi", "Olası Tarihî Eser")
        )
        guven = str(
            bilgi.get("guven", "Belirlenemedi")
        )

        genel = (
            f"# 🏛️ {eser_adi}\n\n"
            f"**Güven düzeyi:** {guven}\n\n"
            "### 📝 Genel Tanıtım\n\n"
            f"{bilgi.get('genel_bakis', 'Bilgi bulunamadı.')}\n\n"
            "### 🌟 Tarihsel Önemi\n\n"
            f"{bilgi.get('tarihsel_onem', 'Bilgi bulunamadı.')}"
        )

        tarihce = (
            "## 📜 Dönem, Uygarlık ve Tarihçe\n\n"
            f"{bilgi.get('tarihce', 'Yeterli bilgi bulunamadı.')}"
        )

        bulgular = (
            "## 🔎 Arkeolojik Bulgular ve Detaylar\n\n"
            f"{bilgi.get('arkeolojik_bulgular', 'Bilgi bulunamadı.')}\n\n"
            "### ⚠️ Belirsizlikler\n\n"
            f"{bilgi.get('belirsizlikler', 'Kesinlik belirlenemedi.')}"
        )

        kaynaklar = (
            "## 📚 Araştırma Kaynakları\n\n"
            "- [UNESCO Dünya Mirası](https://whc.unesco.org/)\n"
            "- [Türkiye Kültür Portalı](https://www.kulturportali.gov.tr/)\n"
            "- [DergiPark Akademik Yayınları](https://dergipark.org.tr/)\n\n"
            "*Bunlar araştırmaya başlamak için önerilen kaynaklardır. "
            "Bu eserle ilgili bilgilerin bu kaynaklarda doğrulandığı "
            "anlamına gelmez. Eserin adı ve tarihi ayrıca "
            "kaynaklar üzerinden kontrol edilmelidir.*"
        )

        return genel, tarihce, bulgular, kaynaklar

    except Exception as hata:
        mesaj = (
            f"### Analiz sırasında hata oluştu\n\n"
            f"`{type(hata).__name__}: {str(hata)[:500]}`\n\n"
            "API anahtarını, bağlantıyı ve Render günlüklerini "
            "kontrol et."
        )
        return mesaj, "", "", ""


# ---------------- TASARIM ----------------

css = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}

body {
    background: #101114 !important;
}

#hero {
    padding: 42px 22px;
    border-radius: 22px;
    text-align: center;
    background: linear-gradient(
        135deg, #202321, #17151b, #292116
    );
    border: 1px solid #806b40;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(30px, 5vw, 48px);
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 22px auto;
    background: linear-gradient(
        90deg, transparent, #e5c47a, transparent
    );
}

button.primary {
    background: linear-gradient(
        90deg, #a77b32, #e2c477
    ) !important;
    color: #17130b !important;
    border: none !important;
    font-weight: bold !important;
}

.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}

@media (max-width: 600px) {
    #hero {
        padding: 65px 15px 30px;
    }
}
"""


with gr.Blocks(
    title="Tarihî Eser Asistanı",
    css=css,
    theme=gr.themes.Base(
        primary_hue="amber",
        neutral_hue="slate"
    )
) as uygulama:

    # Türk bayrağı: CSS seçicisine bağlı kalmadan sabit konum.
    gr.HTML("""
    <div style="
        position: fixed;
        top: 18px;
        right: 22px;
        z-index: 99999;
        pointer-events: none;
    ">
        <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
            alt="Türk Bayrağı"
            style="
                display: block;
                width: 68px;
                height: auto;
                border: 1px solid #e5c47a;
                border-radius: 4px;
                box-shadow: 0 3px 14px rgba(0,0,0,0.45);
            "
        >
    </div>

    <style>
    @media (max-width: 600px) {
        div:has(> img[alt="Türk Bayrağı"]) {
            top: 10px !important;
            right: 10px !important;
        }

        img[alt="Türk Bayrağı"] {
            width: 45px !important;
        }
    }
    </style>
    """)

    gr.HTML("""
    <div id="hero">
        <div style="font-size:42px">🏛️</div>
        <h1>TARİHİN İZİNİ SÜR</h1>
        <div class="gold-line"></div>
        <p>Geçmişin izlerini keşfet. Eserleri tanı, tarihlerini araştır.</p>
        <p style="font-size:12px;letter-spacing:3px">
            TARİH • ARKEOLOJİ • KEŞİF
        </p>
    </div>
    """)

    gr.Markdown("### Yeni bir keşfe hazır mısın?")

    with gr.Group(elem_classes=["panel"]):

        api_anahtar_girdisi = gr.Textbox(
            label="Gemini API Anahtarı",
            placeholder="Gemini API anahtarını gir",
            info=(
                "Render ortamında GEMINI_API_KEY tanımlıysa "
                "bu alanı boş bırakabilirsin."
            ),
            type="password",
            value=""
        )

        fotograf_girdisi = gr.Image(
            label="Eser fotoğrafı yükleyin",
            type="filepath",
            height=320
        )

        arastir_butonu = gr.Button(
            "✦ KEŞFİ BAŞLAT",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():

        with gr.Tab("📜 Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Fotoğraf yükledikten sonra analiz burada görünecek."
            )

        with gr.Tab("🏺 Tarihçe"):
            tarihce_cikti = gr.Markdown(
                "Dönem, uygarlık ve tarihsel bağlam burada görünecek."
            )

        with gr.Tab("🔎 Arkeolojik Bulgular"):
            bulgu_cikti = gr.Markdown(
                "Gözlenen mimari özellikler ve belirsizlikler burada görünecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Araştırma bağlantıları burada görünecek."
            )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[
            fotograf_girdisi,
            api_anahtar_girdisi
        ],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            bulgu_cikti,
            kaynak_cikti
        ],
        show_progress="full"
    )


# Render'ın verdiği portu kullan.
PORT = int(os.environ.get("PORT", "10000"))

uygulama.queue().launch(
    server_name="0.0.0.0",
    server_port=PORT
)
