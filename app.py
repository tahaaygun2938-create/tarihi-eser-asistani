
import os
import base64
from io import BytesIO

import gradio as gr
import requests
from PIL import Image

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def eseri_incele(image_path):
    if not image_path:
        return "Önce bir fotoğraf yükle."

    if not API_KEY:
        return "HATA: Render ayarlarında GEMINI_API_KEY bulunamadı."

    try:
        if isinstance(image_path, dict):
    image_path = image_path.get("path")

if not image_path or not os.path.exists(image_path):
    return "Fotoğraf dosyası bulunamadı. Lütfen fotoğrafı yeniden yükle."

image = Image.open(image_path).convert("RGB")
        image.thumbnail((1200, 1200))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)

        encoded_image = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        prompt = """
Sen tarih, arkeoloji ve sanat tarihi alanlarında yardımcı
olan bir araştırma asistanısın.

Fotoğraftaki nesneyi dikkatlice incele ve Türkçe cevap ver.

Şu başlıkları kullan:
1. Eserin olası adı
2. Görsel özellikleri ve malzemesi
3. Tahmini tarih ve dönem
4. Olası kökeni ve kültürü
5. Tarihî önemi
6. Benzer eserlerle karşılaştırma
7. Sonucu doğrulamak için araştırma önerileri

Önemli kurallar:
- Emin değilsen kesin konuşma.
- Fotoğraftan anlaşılamayan bilgileri uydurma.
- Kaynak veya bağlantı uydurma.
- Birden fazla ihtimal varsa açıkla.
- Nesnenin tarihî eser olmayabileceğini de değerlendir.
- Tahminlerini doğrulanmış bilgilerden ayır.
"""

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            + MODEL
            + ":generateContent"
        )

        response = requests.post(
            url,
            params={"key": API_KEY},
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": encoded_image
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 2000
                }
            },
            timeout=90
        )

        if response.status_code != 200:
            try:
                error = response.json()["error"]["message"]
            except Exception:
                error = response.text[:500]

            return (
                f"API HATASI ({response.status_code})\n\n"
                f"{error}"
            )

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            return "Yapay zekâ yanıt oluşturamadı. Başka bir fotoğraf dene."

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = "\n\n".join(
            part["text"]
            for part in parts
            if "text" in part
        )

        if not answer:
            return "Yanıt boş geldi. Lütfen tekrar dene."

        return (
            "# 🏺 ESER ANALİZİ\n\n"
            + answer
            + "\n\n---\n"
            + "*Bu sonuç yapay zekâ değerlendirmesidir. "
              "Kesin tespit için güvenilir kaynaklardan doğrulama yap.*"
        )

    except requests.exceptions.Timeout:
        return "İstek zaman aşımına uğradı. Tekrar dene."

    except Exception as error:
        return f"Beklenmeyen hata: {str(error)}"



with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="amber",
        secondary_hue="amber",
        neutral_hue="slate"
    ),
    css="""
    body, .gradio-container {
        background: #101114 !important;
        color: #f2eadb !important;
    }

    .gradio-container {
        max-width: 1100px !important;
        margin: auto !important;
    }

    #hero {
        text-align: center;
        padding: 35px 15px 25px;
        border-bottom: 1px solid #554326;
        margin-bottom: 24px;
    }

    #hero h1 {
        color: #d9b56d;
        font-size: 42px;
        letter-spacing: 3px;
        margin-bottom: 10px;
    }

    #hero p {
        color: #c2b9a8;
        font-size: 16px;
    }

    #upload-panel {
        border: 1px solid #725a32;
        border-radius: 16px;
        padding: 18px;
        background: #191a1f;
    }

    #analyze {
        background: linear-gradient(90deg, #8e672b, #d9b56d);
        color: #111111;
        border: none;
        border-radius: 10px;
        font-weight: bold;
        min-height: 52px;
        font-size: 16px;
    }

    #result-panel {
        border: 1px solid #554326;
        border-radius: 16px;
        padding: 20px;
        background: #17181c;
        line-height: 1.8;
    }

    footer {
        visibility: hidden;
    }
    """,
    title="HERITAGE AI | Tarihî Eser Asistanı"
) as demo:

    gr.HTML("""
    <div id="hero">
        <div style="color:#d9b56d;font-size:14px;
                    letter-spacing:5px;margin-bottom:12px;">
            HERITAGE AI
        </div>
        <h1>GEÇMİŞİ KEŞFET</h1>
        <p>
            Tarihî eserleri yapay zekâ ile incele.
            Geçmişin izlerini fotoğraflarla keşfet.
        </p>
        <div style="color:#8e7852;font-size:12px;
                    letter-spacing:2px;margin-top:18px;">
            TARİH • ARKEOLOJİ • KÜLTÜREL MİRAS
        </div>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1, elem_id="upload-panel"):
            gr.Markdown("## 🏺 Eserini tanıt")
            gr.Markdown(
                "İncelemek istediğin eserin fotoğrafını yükle."
            )

            photo = gr.Image(
                type="filepath",
                label="ESER FOTOĞRAFI",
                height=320
            )

            button = gr.Button(
                "⌕  ESERİ İNCELE",
                variant="primary",
                elem_id="analyze"
            )

            gr.Markdown(
                "*Daha iyi sonuçlar için eserin net ve "
                "aydınlık bir fotoğrafını kullan.*"
            )

        with gr.Column(scale=1, elem_id="result-panel"):
            gr.Markdown("## 📜 Eser analizi")
            result = gr.Markdown(
                "Fotoğrafını yükle ve **Eseri İncele** "
                "düğmesine bas. Analiz burada görünecek."
            )

    gr.Markdown("""
    ---
    <div style="text-align:center;color:#a69b87;">
        HERITAGE AI · TARİHÎ ESER ARAŞTIRMA PLATFORMU

        <br><br>
        Yapay zekâ sonuçları tahmin içerebilir.
        Kesin tarih ve kimlik için güvenilir kaynaklardan doğrulama yap.
    </div>
    """)

    button.click(
        fn=eseri_incele,
        inputs=photo,
        outputs=result
    )

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 10000))
)
