
import os
import io
import json
import base64

import requests
import gradio as gr
from PIL import Image


# =========================
# AYARLAR
# =========================

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL_ID = "gemini-3.5-flash-lite"
API_URL = "https://generativelanguage.googleapis.com/v1beta"


# =========================
# GEMINI API
# =========================

def gemini_istegi(prompt, image_data):
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY ortam degiskeni tanimlanmamis."
        )

    url = (
        f"{API_URL}/models/"
        f"{MODEL_ID}:generateContent"
    )

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1600
        }
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY
            },
            json=body,
            timeout=45
        )
    except requests.Timeout:
        raise RuntimeError(
            "Gemini zamaninda yanit vermedi. Tekrar dene."
        )
    except requests.RequestException as error:
        raise RuntimeError(
            f"Baglanti hatasi: {error}"
        )

    if response.status_code != 200:
        try:
            detail = response.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            detail = response.text[:500]

        raise RuntimeError(
            f"Gemini HTTP {response.status_code}: {detail}"
        )

    result = response.json()
    candidates = result.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Model bir analiz sonucu dondurmedi."
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "\n".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not answer:
        raise RuntimeError("Model bos yanit dondurdu.")

    return answer


# =========================
# ESER ANALIZI
# =========================

def eser_ara(fotograf):
    if not fotograf:
        return (
            "Once bir fotograf yukle.",
            "",
            "",
            ""
        )

    try:
        with Image.open(fotograf) as original:
            image = original.convert("RGB")
            image.thumbnail((900, 900))

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=75
            )

            image_data = base64.b64encode(
                buffer.getvalue()
            ).decode("utf-8")

        prompt = """
Fotograftaki tarihi eseri arkeoloji ve sanat tarihi
uzmani gibi dikkatlice incele.

Turkce cevap ver. Asagidaki JSON alanlarini kullan:
{
  "eser_adi": "Olası eser adi",
  "guven": "Dusuk, Orta veya Yuksek",
  "genel_bakis": "Gorulen ozellikler",
  "tarihce": "Olası donem ve tarihsel baglam",
  "bulgular": "Malzeme, bicim ve susleme",
  "onem": "Tarihsel onemi",
  "belirsizlikler": "Bilinmeyenler ve alternatifler"
}

Kurallar:
- Yalnizca gecerli JSON dondur.
- Turkce yaz.
- Emin olmadigin bilgileri kesinmis gibi sunma.
- Eserin adini, tarihini veya yerini uydurma.
- Fotograf uzerinden kesin kimlik tespiti yaptigini iddia etme.
- Kaynaklari kontrol etmediysen kontrol ettigini soyleme.
"""

        answer = gemini_istegi(prompt, image_data)

        # JSON cevabini ayikla.
        if answer.startswith("```"):
            lines = answer.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            answer = "\n".join(lines).strip()

        data = json.loads(answer)

        def field(name, default):
            value = data.get(name, default)
            if value is None:
                return default
            return str(value)

        name = field("eser_adi", "Tanimlanamayan eser")
        confidence = field("guven", "Belirlenemedi")
        overview = field("genel_bakis", "Bilgi bulunamadi.")
        history = field("tarihce", "Tarihce belirlenemedi.")
        findings = field("bulgular", "Bulgu belirtilmedi.")
        importance = field("onem", "Onemi belirlenemedi.")
        uncertainty = field(
            "belirsizlikler",
            "Belirsizlik belirtilmedi."
        )

        overview_md = (
            f"# {name}\n\n"
            f"**Guven duzeyi:** {confidence}\n\n"
            f"## Genel bakis\n{overview}\n\n"
            f"## Tarihsel onemi\n{importance}"
        )

        history_md = (
            f"# Tarihce\n\n{history}\n\n"
            "Bu degerlendirme bagimsiz kaynaklarla "
            "dogrulanmalidir."
        )

        findings_md = (
            f"# Arkeolojik bulgular\n\n{findings}\n\n"
            f"## Belirsizlikler\n{uncertainty}"
        )

        sources_md = """
# Kaynak arastirmasi

Bu analizde bagimsiz kaynak kontrolu yapilmadi.

- [UNESCO Dunya Mirasi Merkezi](https://whc.unesco.org/)
- [T.C. Kultur Portali](https://www.kulturportali.gov.tr/)

Bu baglantilar eserin bu kaynaklarda kayitli oldugunu
tek basina kanitlamaz.

*Bu sonuc on degerlendirmedir.*
"""

        return (
            overview_md,
            history_md,
            findings_md,
            sources_md
        )

    except Exception as error:
        print("ANALIZ HATASI:", repr(error))

        return (
            f"## Analiz basarisiz\n\n{error}",
            "Tarihce olusturulamadi.",
            "Bulgular olusturulamadi.",
            "Kaynak kontrolu yapilmadi."
        )


# =========================
# TASARIM
# =========================

CSS = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}

#hero {
    position: relative;
    padding: 36px 20px;
    border-radius: 20px;
    text-align: center;
    background: linear-gradient(
        135deg, #202321, #17151b, #292116
    );
    border: 1px solid #806b40;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(28px, 5vw, 44px);
}

#hero p {
    color: #e0d8c7;
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 20px auto;
    background: #e5c47a;
}

#turk-bayragi {
    position: absolute;
    top: 14px;
    right: 16px;
    width: 55px;
    border-radius: 3px;
}

button.primary {
    background: #d9b663 !important;
    color: #17130b !important;
    font-weight: bold !important;
}

.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}
"""


# =========================
# ARAYUZ
# =========================

with gr.Blocks(
    title="TarihinIzi",
    theme=gr.themes.Soft(),
    css=CSS
) as app:

    gr.HTML("""
    <div id="hero">
        <img
            id="turk-bayragi"
            src="https://flagcdn.com/w160/tr.png"
            alt="Turk Bayragi"
        >
        <div style="font-size:42px">🏛️</div>
        <h1>TARIHIN IZINI SUR</h1>
        <div class="gold-line"></div>
        <p>Gecmisin izlerini kesfet.</p>
        <p>TARIH • ARKEOLOJI • KESIF</p>
    </div>
    """)

    gr.Markdown(
        "### Eser arastirmasi\n"
        "Bir fotograf yukle ve incelemeyi baslat."
    )

    with gr.Group(elem_classes=["panel"]):
        photo = gr.Image(
            label="Eser fotografi",
            type="filepath",
            height=300
        )

        button = gr.Button(
            "ESERI INCELE",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Arastirma dosyasi")

    with gr.Tabs():
        with gr.Tab("Genel Bakis"):
            overview = gr.Markdown(
                "Analiz burada gorunecek."
            )

        with gr.Tab("Tarihce"):
            history = gr.Markdown(
                "Tarihce burada gorunecek."
            )

        with gr.Tab("Arkeolojik Bulgular"):
            findings = gr.Markdown(
                "Bulgular burada gorunecek."
            )

        with gr.Tab("Kaynaklar"):
            sources = gr.Markdown(
                "Kaynaklar burada gorunecek."
            )

    gr.Markdown(
        "*Sonuclar yapay zeka tarafindan uretilir ve "
        "uzman incelemesinin yerini tutmaz.*"
    )

    button.click(
        fn=eser_ara,
        inputs=[photo],
        outputs=[
            overview,
            history,
            findings,
            sources
        ],
        show_progress="full"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.queue().launch(
        server_name="0.0.0.0",
        server_port=port
    )
