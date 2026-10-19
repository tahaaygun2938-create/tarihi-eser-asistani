
import os
import io
import json
import base64
import requests
import gradio as gr
from PIL import Image

# ==================================================
# AYARLAR
# ==================================================

API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = "gemini-3.5-flash-lite"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()


# ==================================================
# GEMINI API
# ==================================================

def gemini_istegi(govde):
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY tanımlı değil. "
            "API anahtarını ortam değişkenine ekle."
        )

    url = f"{API_URL}/models/{MODEL_ID}:generateContent"

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY
            },
            json=govde,
            timeout=(10, 45)
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Gemini 45 saniyede yanıt vermedi. Tekrar dene."
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"İnternet bağlantısı hatası: {e}")

    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get(
                "message", response.text[:500]
            )
        except Exception:
            detail = response.text[:500]

        if response.status_code == 429:
            raise RuntimeError(
                f"API kotası veya istek sınırı aşıldı: {detail}"
            )
        elif response.status_code in (401, 403):
            raise RuntimeError(
                f"API anahtarı veya erişim izni hatası: {detail}"
            )
        elif response.status_code == 404:
            raise RuntimeError(
                f"Model bulunamadı ({MODEL_ID}): {detail}"
            )
        else:
            raise RuntimeError(
                f"Gemini HTTP {response.status_code}: {detail}"
            )

    return response.json()


# ==================================================
# FOTOĞRAF ANALİZİ
# ==================================================

def eser_ara(fotograf):
    if fotograf is None:
        return (
            "Önce bir eser fotoğrafı yükle.",
            "",
            "",
            ""
        )

    try:
        # Fotoğrafı hazırla
        with Image.open(fotograf) as original:
            image = original.convert("RGB")
            image.thumbnail((900, 900))

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=75,
                optimize=True
            )

            image_base64 = base64.b64encode(
                buffer.getvalue()
            ).decode("utf-8")

        prompt = """
Fotoğraftaki tarihî veya arkeolojik eseri dikkatlice incele.
Türkçe cevap ver. Yalnızca geçerli JSON üret.

Şu alanları kullan:
{
  "eser_adi": "Eserin olası adı veya tanımlanamıyor",
  "guven": "Düşük, Orta veya Yüksek; gerekçesiyle",
  "genel_bakis": "Fotoğrafta görülen özellikler",
  "tarihce": "Olası dönem ve tarihsel bağlam",
  "arkeolojik_bulgular": "Malzeme, biçim ve süsleme",
  "tarihsel_onem": "Tarihsel önemi",
  "belirsizlikler": "Bilinmeyenler ve alternatif ihtimaller"
}

Kurallar:
- Görselde görülenleri tahminlerden ayır.
- Eserin adını, tarihini veya bulunduğu yeri uydurma.
- Emin değilsen güven düzeyini düşük tut.
- Dış kaynaklara bakmadıysan kaynak doğruladığını iddia etme.
- JSON dışında metin yazma.
"""

        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1600,
                "responseMimeType": "application/json"
            }
        }

        result = gemini_istegi(body)

        candidates = result.get("candidates", [])
        if not candidates:
            reason = result.get("promptFeedback", {}).get(
                "blockReason", "Bilinmiyor"
            )
            raise RuntimeError(
                f"Model yanıt oluşturmadı. Neden: {reason}"
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(
            part.get("text", "")
            for part in parts
            if part.get("text")
        ).strip()

        if not text:
            raise RuntimeError("Model boş yanıt verdi.")

        # Olası Markdown kod çitlerini temizle
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        data = json.loads(text)

        def get_field(key, default):
            value = data.get(key, default)
            if value is None:
                return default
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value).strip() or default

        name = get_field("eser_adi", "Tanımlanamayan eser")
        confidence = get_field("guven", "Belirlenemedi")
        overview = get_field("genel_bakis", "Bilgi bulunamadı.")
        history = get_field("tarihce", "Tarihçe belirlenemedi.")
        findings = get_field(
            "arkeolojik_bulgular", "Bulgu belirtilmedi."
        )
        importance = get_field(
            "tarihsel_onem", "Önemi belirlenemedi."
        )
        uncertainty = get_field(
            "belirsizlikler", "Belirsizlik belirtilmedi."
        )

        overview_output = (
            f"# 🏛️ {name}\n\n"
            f"**Güven düzeyi:** {confidence}\n\n"
            f"### 📝 Genel bakış\n{overview}\n\n"
            f"### 🌟 Tarihsel önemi\n{importance}"
        )

        history_output = (
            f"## 📜 Tarihçe\n\n{history}\n\n"
            "Bu değerlendirme bağımsız kaynaklarla doğrulanmalıdır."
        )

        findings_output = (
            f"## 🔎 Arkeolojik bulgular\n\n{findings}\n\n"
            f"### ⚠️ Belirsizlikler\n{uncertainty}"
        )

        sources_output = """
## 📚 Kaynaklar

Bu analiz sırasında belirli eser kayıtları bağımsız olarak
doğrulanmadı. Araştırmaya başlamak için:

- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [T.C. Kültür Portalı](https://www.kulturportali.gov.tr/)

Bu bağlantılar, eserin bu kaynaklarda kayıtlı olduğunu kanıtlamaz.

*Bu sonuç ön değerlendirmedir; uzman incelemesinin yerini tutmaz.*
"""

        return (
            overview_output,
            history_output,
            findings_output,
            sources_output
        )

    except Exception as e:
        print("ANALİZ HATASI:", repr(e))
        message = str(e)

        return (
            f"## ⚠️ Analiz başarısız\n\n{message}",
            "Tarihçe oluşturulamadı.",
            "Arkeolojik bulgular oluşturulamadı.",
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
    padding: 40px 20px;
    border-radius: 20px;
    text-align: center;
    background: linear-gradient(135deg, #202321, #17151b, #292116);
    border: 1px solid #806b40;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(28px, 5vw, 46px);
}

#hero p {
    color: #e0d8c7;
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 20px auto;
    background: linear-gradient(90deg, transparent, #e5c47a, transparent);
}

#turk-bayragi {
    position: absolute;
    top: 16px;
    right: 18px;
    width: 60px;
    border-radius: 3px;
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
        width: 40px;
        top: 8px;
        right: 8px;
    }
}
"""


# ==================================================
# ARAYÜZ
# ==================================================

with gr.Blocks(
    title="Tarihinİzi",
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
        photo_input = gr.Image(
            label="Eser fotoğrafı",
            type="filepath",
            height=320
        )

        analyze_button = gr.Button(
            "✦ ESERİ İNCELE",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():
        with gr.Tab("📜 Genel Bakış"):
            overview_output = gr.Markdown(
                "Eser tanıtımı burada görünecek."
            )

        with gr.Tab("🏺 Tarihçe"):
            history_output = gr.Markdown(
                "Tarihçe burada görünecek."
            )

        with gr.Tab("🔎 Arkeolojik Bulgular"):
            findings_output = gr.Markdown(
                "Bulgular burada görünecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            sources_output = gr.Markdown(
                "Kaynak kontrolü burada görünecek."
            )

    gr.Markdown(
        "*Yapay zekâ destekli ön araştırma aracıdır. "
        "Sonuçlar uzman doğrulamasının yerini tutmaz.*"
    )

    analyze_button.click(
        fn=eser_ara,
        inputs=photo_input,
        outputs=[
            overview_output,
            history_output,
            findings_output,
            sources_output
        ],
        show_progress="full"
    )


if __name__ == "__main__":
    uygulama.queue().launch()
