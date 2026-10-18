
import os
import io
import json
import time
import base64
import getpass
import requests
import gradio as gr
from PIL import Image

# ==================================================
# AYARLAR
# ==================================================

API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = "gemini-3.5-flash-lite"

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not API_KEY:
    try:
        API_KEY = getpass.getpass("Gemini API anahtarını gir: ").strip()
    except Exception:
        API_KEY = ""

if not API_KEY:
    raise RuntimeError(
        "API anahtarı bulunamadı. GEMINI_API_KEY ortam "
        "değişkenini ayarla veya uygulamayı terminalden çalıştır."
    )


# ==================================================
# MODEL KONTROLÜ
# ==================================================

def model_kontrol():
    try:
        r = requests.get(
            f"{API_URL}/models",
            headers={"x-goog-api-key": API_KEY},
            timeout=20
        )
    except requests.RequestException as e:
        print("Model kontrolü yapılamadı:", e)
        return

    if r.status_code != 200:
        print("Model kontrolü uyarısı:", r.status_code)
        return

    modeller = r.json().get("models", [])

    bulunan = next(
        (
            m for m in modeller
            if m.get("name", "").removeprefix("models/") == MODEL_ID
        ),
        None
    )

    if bulunan is None:
        raise RuntimeError(
            f"{MODEL_ID} bu API anahtarı için listelenmiyor. "
            "Google AI Studio'daki model erişimini kontrol et."
        )

    if "generateContent" not in bulunan.get(
        "supportedGenerationMethods", []
    ):
        raise RuntimeError(
            f"{MODEL_ID}, generateContent desteklemiyor."
        )


model_kontrol()


# ==================================================
# GEMINI İSTEĞİ
# ==================================================

def gemini_istegi(govde):
    url = f"{API_URL}/models/{MODEL_ID}:generateContent"

    for deneme in range(2):
        try:
            r = requests.post(
                url,
                headers={
                    "x-goog-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                json=govde,
                timeout=120
            )
        except requests.RequestException as e:
            if deneme == 0:
                time.sleep(2)
                continue
            raise RuntimeError(f"Bağlantı hatası: {e}")

        if r.status_code == 200:
            return r.json()

        try:
            detay = r.json().get("error", {}).get(
                "message", r.text[:500]
            )
        except Exception:
            detay = r.text[:500]

        if r.status_code == 429:
            raise RuntimeError(
                "Gemini API kullanım kotası dolmuş olabilir (429). "
                "Google AI Studio'daki kullanım limitlerini kontrol et. "
                "Bu hata için tekrar tekrar istek gönderilmeyecek.\n\n"
                + detay
            )

        if r.status_code in (401, 403):
            raise RuntimeError(
                "API anahtarı geçersiz olabilir veya erişim "
                "izni yok. Anahtarını ve proje ayarlarını kontrol et.\n\n"
                + detay
            )

        if r.status_code in (500, 502, 503, 504) and deneme == 0:
            time.sleep(2)
            continue

        raise RuntimeError(f"Gemini HTTP {r.status_code}: {detay}")

    raise RuntimeError("İstek tamamlanamadı.")


# ==================================================
# ESER ANALİZİ
# ==================================================

def eser_ara(fotograf):
    if fotograf is None:
        return (
            "Önce bir fotoğraf yükle.",
            "",
            "",
            ""
        )

    try:
        with Image.open(fotograf) as im:
            im = im.convert("RGB")
            im.thumbnail((1200, 1200))

            tampon = io.BytesIO()
            im.save(tampon, format="JPEG", quality=82)
            foto_data = base64.b64encode(
                tampon.getvalue()
            ).decode("utf-8")

        prompt = """
Sen dikkatli bir arkeoloji ve sanat tarihi araştırma
asistanısın. Fotoğrafı incele ve yalnızca geçerli JSON döndür.

JSON alanları:
{
  "eser_adi": "Olası eser adı",
  "guven": "Düşük, Orta veya Yüksek ve gerekçesi",
  "genel_bakis": "Fotoğrafta görülen özellikler",
  "tarihce": "Olası dönem ve tarihsel bağlam",
  "arkeolojik_bulgular": "Malzeme, biçim ve süsleme ayrıntıları",
  "tarihsel_onem": "Bilinen önemi veya belirsizlik",
  "belirsizlikler": "Alternatif tanımlamalar ve eksik kanıtlar"
}

Kurallar:
- Türkçe yanıt ver.
- Gözlemi tahminden ayır.
- Emin değilsen bunu açıkça söyle.
- Eserin adını, tarihini veya bulunduğu yeri uydurma.
- Fotoğraftan kesin kimlik tespiti yaptığını iddia etme.
- Gerçek kaynaklara bakmadıysan kaynak doğruladığını söyleme.
- Belirsizlikleri dürüstçe açıkla.
"""

        govde = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": foto_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 2500
            }
        }

        sonuc = gemini_istegi(govde)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            return (
                "Model analiz üretemedi.",
                "",
                "Fotoğraf yeniden denenebilir.",
                "Kaynak doğrulaması yapılmadı."
            )

        parcalar = adaylar[0].get("content", {}).get("parts", [])
        metin = "\n".join(
            p.get("text", "")
            for p in parcalar
            if p.get("text")
        ).strip()

        if not metin:
            raise RuntimeError("Model boş yanıt verdi.")

        bilgi = json.loads(metin)

        def alan(ad, varsayilan):
            deger = bilgi.get(ad, varsayilan)
            return str(deger).strip()

        eser = alan("eser_adi", "Tanımlanamayan eser")
        guven = alan("guven", "Belirlenemedi")
        genel = alan("genel_bakis", "Bilgi bulunamadı.")
        tarih = alan("tarihce", "Tarihçe kesinleştirilemedi.")
        bulgu = alan("arkeolojik_bulgular", "Bulgu belirtilmedi.")
        onem = alan("tarihsel_onem", "Önemi kesinleştirilemedi.")
        belirsizlik = alan("belirsizlikler", "Belirsizlik belirtilmedi.")

        genel_cikti = (
            f"# 🏛️ {eser}\n\n"
            f"**Tahmini güven düzeyi:** {guven}\n\n"
            f"### 📝 Genel tanıtım\n{genel}\n\n"
            f"### 🌟 Tarihsel önemi\n{onem}"
        )

        tarih_cikti = (
            f"## 📜 Dönem, uygarlık ve tarihçe\n\n{tarih}\n\n"
            "Bu tarihsel değerlendirme bağımsız kaynaklarla "
            "doğrulanmalıdır."
        )

        bulgu_cikti = (
            f"## 🔎 Arkeolojik bulgular\n\n{bulgu}\n\n"
            f"### ⚠️ Belirsizlikler\n{belirsizlik}"
        )

        kaynak_cikti = """
## 📚 Kaynak kontrolü

Bu analiz sırasında belirli eser kayıtları bağımsız olarak
doğrulanmadı. Aşağıdaki bağlantılar araştırmaya başlamak içindir:

- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [T.C. Kültür Portalı](https://www.kulturportali.gov.tr/)

Bu ana sayfalar, analiz edilen esere ait doğrulanmış kayıt
bulunduğu anlamına gelmez.

*Bu sonuç bir ön değerlendirmedir; uzman incelemesinin yerini tutmaz.*
"""

        return (
            genel_cikti,
            tarih_cikti,
            bulgu_cikti,
            kaynak_cikti
        )

    except Exception as e:
        hata = str(e)
        print("ESER ANALİZ HATASI:", repr(e))

        return (
            f"## ⚠️ Analiz tamamlanamadı\n\n{hata}",
            "Tarihçe üretilemedi.",
            "Bulgular üretilemedi.",
            "Bu denemede kaynak doğrulaması yapılmadı."
        )


# ==================================================
# TASARIM
# ==================================================

css = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}

#hero {
    position: relative;
    padding: 42px 22px;
    border-radius: 22px;
    text-align: center;
    background: linear-gradient(135deg, #202321, #17151b, #292116);
    border: 1px solid #806b40;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(28px, 5vw, 46px);
    text-shadow: 0 0 12px #806b40;
}

#hero p {
    color: #e0d8c7;
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 22px auto;
    background: linear-gradient(90deg, transparent, #e5c47a, transparent);
}

#turk-bayragi {
    position: absolute;
    top: 18px;
    right: 20px;
    width: 65px;
    border-radius: 3px;
    box-shadow: 0 2px 10px rgba(0,0,0,.4);
}

button.primary {
    background: linear-gradient(90deg, #a77b32, #e2c477) !important;
    color: #17130b !important;
    font-weight: bold !important;
    border: none !important;
}

.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}

@media (max-width: 600px) {
    #turk-bayragi {
        width: 42px;
        top: 10px;
        right: 10px;
    }
}
"""


# ==================================================
# GRADIO ARAYÜZÜ
# ==================================================

with gr.Blocks(
    title="Tarihî Eser Asistanı",
    theme=gr.themes.Soft(),
    css=css
) as uygulama:

    gr.HTML("""
    <div id="hero">
      <img id="turk-bayragi"
           src="https://flagcdn.com/w160/tr.png"
           alt="Türk Bayrağı">
      <div style="font-size:42px">🏛️</div>
      <h1>TARİHİN İZİNİ SÜR</h1>
      <div class="gold-line"></div>
      <p>Geçmişin izlerini keşfet. Eserleri tanı, tarihlerini araştır.</p>
      <p style="font-size:12px;letter-spacing:3px">
        TARİH • ARKEOLOJİ • KEŞİF
      </p>
    </div>
    """)

    gr.Markdown(
        "### Yeni bir keşfe hazır mısın?\n"
        "Bir eser fotoğrafı yükle ve araştırmayı başlat."
    )

    with gr.Group(elem_classes=["panel"]):
        fotograf_girdisi = gr.Image(
            label="Eser fotoğrafı",
            type="filepath",
            height=320
        )

        arastir_butonu = gr.Button(
            "✦  ESERİ İNCELE",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():
        with gr.Tab("📜 Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Eser tanıtımı burada görünecek."
            )

        with gr.Tab("🏺 Tarihçe"):
            tarihce_cikti = gr.Markdown(
                "Tarihçe burada görünecek."
            )

        with gr.Tab("🔎 Arkeolojik Bulgular"):
            bulgu_cikti = gr.Markdown(
                "Bulgular burada görünecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Kaynak kontrolü burada görünecek."
            )

    gr.Markdown(
        "*Yapay zekâ destekli ön araştırma aracıdır. "
        "Sonuçlar uzman doğrulamasının yerini tutmaz.*"
    )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[fotograf_girdisi],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            bulgu_cikti,
            kaynak_cikti
        ],
        show_progress="full"
    )


import os

port = int(os.environ.get("PORT", 10000))
demo.launch(server_name="0.0.0.0", server_port=port)
