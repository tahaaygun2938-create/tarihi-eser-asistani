import os
import json
import base64
import requests
import gradio as gr
from PIL import Image
from io import BytesIO

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def eseri_incele(image):
    if image is None:
        return "Önce bir eser fotoğrafı yükle.", "", "", ""

    if not GOOGLE_VISION_API_KEY or not GEMINI_API_KEY:
        return (
            "API anahtarları henüz ayarlanmamış. Render ayarlarına eklemelisin.",
            "", "", ""
        )

    try:
        # Fotoğrafı JPEG formatına dönüştür
        img = Image.open(image).convert("RGB")
        img.thumbnail((1200, 1200))

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        image_bytes = buffer.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Google Vision ile benzer internet sonuçlarını ara
        vision_url = (
            "https://vision.googleapis.com/v1/images:annotate"
            f"?key={GOOGLE_VISION_API_KEY}"
        )

        vision_payload = {
            "requests": [{
                "image": {"content": image_b64},
                "features": [
                    {"type": "WEB_DETECTION", "maxResults": 10},
                    {"type": "LABEL_DETECTION", "maxResults": 10}
                ]
            }]
        }

        vr = requests.post(
            vision_url, json=vision_payload, timeout=45
        )
        vr.raise_for_status()
        vision_data = vr.json()["responses"][0]

        if "error" in vision_data:
            raise Exception(vision_data["error"].get("message", "Vision hatası"))

        web = vision_data.get("webDetection", {})
        entities = [
            item.get("description", "")
            for item in web.get("webEntities", [])
            if item.get("description")
        ]

        labels = [
            item.get("description", "")
            for item in vision_data.get("labelAnnotations", [])
            if item.get("description")
        ]

        pages = [
            {
                "title": p.get("pageTitle", "Başlıksız sayfa"),
                "url": p.get("url", "")
            }
            for p in web.get("pagesWithMatchingImages", [])
            if p.get("url")
        ][:8]

        visual_references = (
            "Görsel etiketleri: " + ", ".join(labels[:10]) + "\n"
            "Benzer web varlıkları: " + ", ".join(entities[:10]) + "\n"
            "Benzer görsellerin bulunduğu sayfalar:\n"
            + "\n".join(
                f"- {p['title']}: {p['url']}" for p in pages
            )
        )

        # Gemini'ye fotoğrafı ve web bulgularını gönder
        prompt = f"""
Sen arkeoloji ve sanat tarihi konusunda yardımcı olan
bir araştırma asistanısın.

Fotoğrafı dikkatle incele. Google Vision sonuçlarını da
yardımcı kanıt olarak kullan:

{visual_references}

Türkçe yanıt ver ve aşağıdaki başlıkları kullan:

1. ESERİN OLASI ADI
2. TANIM VE GÖRSEL ÖZELLİKLER
3. TAHMİNİ DÖNEM VE TARİH
4. KÖKEN VE KÜLTÜR
5. TARİHSEL VE ARKEOLOJİK ÖNEM
6. BELİRSİZLİKLER VE DOĞRULAMA

Önemli kurallar:
- Yalnızca fotoğrafa bakarak kesin kimlik iddiasında bulunma.
- Benzerlik sonuçlarını doğrulanmış kimlik gibi sunma.
- Bilinmeyen tarih, kültür, kazı yeri veya müze bilgilerini uydurma.
- Kanıt yetersizse bunu açıkça söyle.
- Fotoğraftaki nesnenin eser olmayabileceğini de değerlendir.
- Web sonuçlarının bağlantılarını kaynaklar bölümünde ayrıca ver.
- Güvenilir kaynaklar ile yalnızca benzer görsel içeren sayfaları ayır.
"""

        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent"
            f"?key={GEMINI_API_KEY}"
        )

        gemini_payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2500
            }
        }

        grr = requests.post(
            gemini_url, json=gemini_payload, timeout=90
        )
        grr.raise_for_status()
        result = grr.json()

        answer = result["candidates"][0]["content"]["parts"][0]["text"]

        source_text = "## Google Vision bulguları\n\n"
        source_text += "**Görsel etiketleri:** " + (
            ", ".join(labels) if labels else "Sonuç bulunamadı."
        )
        source_text += "\n\n**Benzer web varlıkları:** " + (
            ", ".join(entities) if entities else "Sonuç bulunamadı."
        )
        source_text += "\n\n## İncelenebilecek bağlantılar\n\n"

        if pages:
            for p in pages:
                source_text += f"- [{p['title']}]({p['url']})\n"
        else:
            source_text += "Benzer görseller için sayfa bulunamadı.\n"

        source_text += (
            "\n**Not:** Bu bağlantılar eserin kimliğini tek başına "
            "kanıtlamaz. Bilgileri güvenilir müze ve akademik "
            "kaynaklardan doğrulamak gerekir."
        )

        return answer, answer, answer, source_text

    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text[:800]
        except Exception:
            pass
        msg = f"API isteği başarısız oldu: {e}\n{detail}"
        return msg, "", "", ""

    except Exception as e:
        msg = f"İnceleme sırasında hata oluştu: {e}"
        return msg, "", "", ""


with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="amber",
        neutral_hue="slate"
    ),
    title="Tarihî Eser Asistanı"
) as demo:

    gr.Markdown("""
    # 🏺 TARİHÎ ESER ASİSTANI
    ### Fotoğraf yükle, olası kimliğini ve tarihsel bağlamını araştır.

    *Yapay zekâ sonuçları araştırma amaçlıdır; uzman doğrulamasının
    yerini tutmaz.*
    """)

    with gr.Row():
        with gr.Column(scale=1):
            photo = gr.Image(
                type="filepath",
                label="Eser fotoğrafı",
                height=350
            )
            analyze = gr.Button(
                "🔎 ESERİ İNCELE",
                variant="primary"
            )

        with gr.Column(scale=2):
            overview = gr.Markdown(
                label="İnceleme sonucu"
            )

    with gr.Tabs():
        with gr.Tab("Genel Bakış"):
            general = gr.Markdown()
        with gr.Tab("Tarih ve Arkeoloji"):
            archaeology = gr.Markdown()
        with gr.Tab("Kaynaklar"):
            sources = gr.Markdown()

    analyze.click(
        fn=eseri_incele,
        inputs=[photo],
        outputs=[overview, general, archaeology, sources]
    )

demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 10000))
)
