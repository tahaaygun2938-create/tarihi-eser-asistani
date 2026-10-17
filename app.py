
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
    theme=gr.themes.Soft(
        primary_hue="amber",
        neutral_hue="slate"
    ),
    title="Tarihî Eser Asistanı"
) as demo:

    gr.Markdown("""
    # 🏺 TARİHÎ ESER ASİSTANI
    ### Geçmişin izlerini fotoğraflarla keşfet.

    Bir eser fotoğrafı yükle. Yapay zekâ olası kimliğini,
    dönemini ve tarihî önemini değerlendirsin.
    """)

    photo = gr.Image(
        type="filepath",
        label="Eser fotoğrafını yükle",
        height=350
    )

    button = gr.Button(
        "🔎 ESERİ İNCELE",
        variant="primary"
    )

    result = gr.Markdown(label="Analiz sonucu")

    button.click(
        fn=eseri_incele,
        inputs=photo,
        outputs=result
    )

    gr.Markdown("""
    ---
    **Bilgilendirme:** Sonuçlar kesin arkeolojik tespit değildir.
    Bu uygulama tek başına canlı internet araştırması yapmaz.
    """)

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 10000))
)
