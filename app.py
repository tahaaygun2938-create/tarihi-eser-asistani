
import os
import json
import base64
from io import BytesIO

import requests
import gradio as gr
from PIL import Image


# =====================================================
# TARIHINIZI - MODEL VE API AYARLARI
# =====================================================

MODEL = "gemini-3.5-flash-lite"

API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or ""
).strip()

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

SECTIONS = [
    "Genel Bilgi",
    "Tarihçe",
    "Dönem ve Tarih",
    "Coğrafi Konum",
    "Mimari ve Üslup",
    "Malzeme ve Teknik",
    "Kullanım Amacı",
    "Kültürel Önemi",
    "Yazıt ve Semboller",
    "Benzer Eserler",
    "Koruma Durumu",
    "Eserin Kimliği",
    "Kaynaklar",
    "Kısa Özet",
]


# =====================================================
# GÖRSEL HAZIRLAMA
# =====================================================

def prepare_image(image_path):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((1600, 1600))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)

        return base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")


# =====================================================
# SONUÇ YARDIMCILARI
# =====================================================

def empty_result(message):
    return [message] + [""] * (len(SECTIONS) - 1)


def extract_json(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])

        raise ValueError(
            "Modelin cevabı geçerli JSON biçiminde değil."
        )


def extract_sources(candidate):
    metadata = candidate.get("groundingMetadata", {})
    chunks = metadata.get("groundingChunks", [])

    sources = []
    seen = set()

    for chunk in chunks:
        source = chunk.get("web", {})
        title = source.get("title", "Kaynak")
        url = source.get("uri", "")

        if url and url not in seen:
            seen.add(url)
            sources.append(f"- [{title}]({url})")

    if not sources:
        return (
            "Bu yanıtta Google Arama kaynak bağlantısı döndürmedi. "
            "Bilgileri bağımsız kaynaklardan doğrula."
        )

    return "\n".join(sources)


# =====================================================
# GEMINI İLE TARİHÎ ESER ARAŞTIRMASI
# =====================================================

def research_artifact(image_path, extra_info):

    if not API_KEY:
        return empty_result(
            "## API anahtarı bulunamadı\n\n"
            "Render → Environment bölümünde `GEMINI_API_KEY` "
            "değişkenini kontrol et."
        )

    if not image_path:
        return empty_result(
            "Lütfen önce bir tarihî eser fotoğrafı yükle."
        )

    try:
        image_data = prepare_image(image_path)

        details = (extra_info or "").strip()
        if not details:
            details = "Kullanıcı ek bilgi vermedi."

        prompt = f"""
Sen Tarihinİzi isimli tarihî eser araştırma uygulamasının
uzman araştırma asistanısın.

Yüklenen görseli incele ve eseri araştır.

KULLANICININ EK BİLGİSİ:
{details}

ARAŞTIRMA KURALLARI:
- Görseldeki eserin kimliğini dikkatlice değerlendir.
- Google Arama aracını kullanarak bilgileri karşılaştır.
- Müze, resmî kültür kurumu ve akademik kaynakları tercih et.
- Kesin olmayan bilgileri kesinmiş gibi sunma.
- Tarih, sanatçı, konum veya dönem uydurma.
- Görselde okunmayan yazıları kendin tamamlayıp gerçekmiş
  gibi gösterme.
- Bulunamayan bilgileri "Doğrulanamadı" olarak belirt.
- Eserin kimliği belirsizse alternatifleri ve nedenlerini açıkla.
- Türkçe cevap ver.
- Kaynak bağlantılarını yalnızca gerçekten elde ettiğinde yaz.

Aşağıdaki anahtarların tamamını içeren bir JSON nesnesi üret.
JSON dışında açıklama veya Markdown kod bloğu yazma.
Her anahtarın değeri metin olsun.

Anahtarlar:
{json.dumps(SECTIONS, ensure_ascii=False)}

İçerik:
Genel Bilgi: Eserin tanımı ve temel özellikleri.
Tarihçe: Eserin bilinen geçmişi.
Dönem ve Tarih: Yapım tarihi ve tarihsel dönem.
Coğrafi Konum: Bulunduğu veya keşfedildiği yer.
Mimari ve Üslup: Mimari ve sanatsal özellikler.
Malzeme ve Teknik: Malzemeler ve yapım yöntemi.
Kullanım Amacı: Tarihsel işlevi.
Kültürel Önemi: Kültürel ve tarihî değeri.
Yazıt ve Semboller: Görülebilen yazılar ve semboller.
Benzer Eserler: Güvenilir biçimde belirlenen benzer örnekler.
Koruma Durumu: Biliniyorsa mevcut koruma durumu.
Eserin Kimliği: Kimlik tespiti ve belirsizlikler.
Kaynaklar: Kullanılan kaynaklar.
Kısa Özet: Önemli bulguların özeti.
"""

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data,
                            }
                        },
                    ],
                }
            ],
            "tools": [
                {"google_search": {}}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 6000,
            },
        }

        print(f"TARIHINIZI_MODEL={MODEL}", flush=True)

        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY,
            },
            json=payload,
            timeout=120,
        )

        print(
            f"GEMINI_HTTP_STATUS={response.status_code}",
            flush=True,
        )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if not response.ok:
            error = data.get("error", {})
            message = error.get(
                "message",
                response.text[:3000] or "Açıklama yok.",
            )

            print(
                "GEMINI_ERROR="
                + json.dumps(data, ensure_ascii=False)[:5000],
                flush=True,
            )

            if response.status_code == 429:
                return empty_result(
                    "## Gemini kota hatası (429)\n\n"
                    f"**İstenen model:** `{MODEL}`\n\n"
                    f"**Google'ın hata mesajı:**\n\n{message}\n\n"
                    "Google AI Studio'da doğru projeyi ve model "
                    "kotasını kontrol et. Kod doğru modeli istese "
                    "bile Google isteği kota nedeniyle reddedebilir."
                )

            if response.status_code in (401, 403):
                return empty_result(
                    "## API erişim hatası\n\n"
                    f"{message}\n\n"
                    "Render'daki API anahtarını ve Google "
                    "projesini kontrol et."
                )

            return empty_result(
                f"## Gemini API hatası ({response.status_code})\n\n"
                f"{message}"
            )

        candidates = data.get("candidates", [])

        if not candidates:
            reason = data.get(
                "promptFeedback", {}
            ).get("blockReason", "Açıklama yok")

            return empty_result(
                f"Google API cevap döndürmedi.\n\nSebep: {reason}"
            )

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])

        response_text = "\n".join(
            part.get("text", "")
            for part in parts
            if part.get("text")
        )

        if not response_text.strip():
            return empty_result(
                "Model metin döndürmedi. Başka bir fotoğrafla "
                "tekrar deneyebilirsin."
            )

        result = extract_json(response_text)

        outputs = [
            str(result.get(section, "Bu bölüm için bilgi bulunamadı."))
            for section in SECTIONS
        ]

        outputs[12] += (
            "\n\n### Google Arama kaynak bağlantıları\n\n"
            + extract_sources(candidate)
        )

        outputs[0] = (
            f"**Araştırma modeli:** `{MODEL}`\n\n"
            + outputs[0]
        )

        print("TARIHINIZI_ARAMA_BASARILI", flush=True)

        return outputs

    except requests.Timeout:
        print("GEMINI_ERROR=Timeout", flush=True)
        return empty_result(
            "Google API zamanında cevap vermedi. Biraz sonra "
            "tekrar deneyebilirsin."
        )

    except requests.RequestException as exc:
        print(
            f"GEMINI_NETWORK_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            "Google API bağlantısı kurulamadı. Render Logs "
            "bölümünü kontrol et."
        )

    except (ValueError, TypeError, KeyError) as exc:
        print(
            f"GEMINI_RESPONSE_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            f"Sonuç işlenirken hata oluştu:\n\n{exc}"
        )

    except Exception as exc:
        print(
            f"GEMINI_UNEXPECTED_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            "Beklenmeyen hata oluştu. Render Logs bölümünü kontrol et."
        )


# =====================================================
# TÜRK TEMALI TASARIM
# =====================================================

CSS = """
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
    background: #fff7f7 !important;
}

body {
    background: #fff7f7 !important;
}

/* Kırmızı Türk bayrağı esintili başlık */
#main-header {
    background: linear-gradient(
        135deg,
        #b00020 0%,
        #e30a17 55%,
        #8f0018 100%
    ) !important;
    color: #ffffff !important;
    border-radius: 16px !important;
    padding: 28px !important;
    margin-bottom: 20px !important;
    text-align: center !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    box-shadow: 0 5px 18px rgba(143,0,24,0.15) !important;
}

#main-header h1 {
    color: #ffffff !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    margin: 0 0 8px 0 !important;
    letter-spacing: 0.5px !important;
}

#main-header p {
    color: #fff0f0 !important;
    font-size: 15px !important;
    margin: 0 !important;
}

/* Araştırma butonu */
#research-button {
    background: linear-gradient(
        90deg,
        #b00020,
        #e30a17
    ) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    transition: 0.2s ease !important;
}

#research-button:hover {
    background: #8f0018 !important;
}

/* Beyaz içerik alanları */
.gr-panel,
.gr-box,
.gr-group {
    border-radius: 12px !important;
}

/* Form alanları */
button,
input,
textarea {
    border-radius: 8px !important;
}

/* Aktif sekme */
button.selected {
    border-bottom: 3px solid #e30a17 !important;
    color: #b00020 !important;
    font-weight: 700 !important;
}

/* Temiz görünüm */
footer {
    display: none !important;
}
"""


# =====================================================
# UYGULAMA ARAYÜZÜ
# =====================================================

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="rose",
        neutral_hue="slate",
    ),
    css=CSS,
    title="Tarihinİzi",
) as demo:

    gr.HTML("""
    <div id="main-header">
        <h1>🇹🇷 Tarihinİzi</h1>
        <p>
            Geçmişin izlerini keşfet.
            Türk tarihinin ve dünya mirasının izini sür.
        </p>
    </div>
    """)

    gr.Markdown(
        f"**Aktif model:** `{MODEL}`\n\n"
        "Bir eser fotoğrafı yükle, araştırmayı başlat ve "
        "bulguları ayrı sekmelerde incele."
    )

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label="Tarihî eser fotoğrafı",
                type="filepath",
                height=320,
            )

            extra_info = gr.Textbox(
                label="Ek bilgi (isteğe bağlı)",
                placeholder=(
                    "Örneğin: Bulunduğu şehir, köy, müze "
                    "veya eser üzerindeki yazılar..."
                ),
                lines=3,
            )

            research_button = gr.Button(
                "🔎 Eseri Araştır",
                variant="primary",
                elem_id="research-button",
            )

        with gr.Column(scale=2):
            result_boxes = []

            with gr.Tabs():
                for section in SECTIONS:
                    with gr.Tab(section):
                        output = gr.Markdown(
                            "Fotoğraf yükleyip araştırmayı "
                            "başlattığında sonuçlar burada görünür."
                        )
                        result_boxes.append(output)

    research_button.click(
        fn=research_artifact,
        inputs=[image_input, extra_info],
        outputs=result_boxes,
        show_progress="full",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    demo.queue(
        default_concurrency_limit=2
    ).launch(
        server_name="0.0.0.0",
        server_port=port,
    )
