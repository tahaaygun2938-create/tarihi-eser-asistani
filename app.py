
import os
import json
import base64
from io import BytesIO

import requests
import gradio as gr
from PIL import Image


# ==================================================
# TARIHINIZI - AYARLAR
# ==================================================

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


# ==================================================
# GÖRSEL İŞLEME
# ==================================================

def prepare_image(image_path):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((1600, 1600))

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)

        return base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")


# ==================================================
# GEMINI CEVABINI İŞLEME
# ==================================================

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

        if start != -1 and end > start:
            return json.loads(text[start:end + 1])

        raise ValueError(
            "Model geçerli bir JSON cevabı döndürmedi."
        )


def get_sources(candidate):
    metadata = candidate.get("groundingMetadata", {})
    chunks = metadata.get("groundingChunks", [])

    sources = []
    seen = set()

    for chunk in chunks:
        web_source = chunk.get("web", {})
        title = web_source.get("title", "Kaynak")
        url = web_source.get("uri", "")

        if url and url not in seen:
            seen.add(url)
            sources.append(f"- [{title}]({url})")

    if not sources:
        return (
            "Bu yanıtta Google Arama tarafından kaynak bağlantısı "
            "döndürülmedi. Bilgileri bağımsız kaynaklardan doğrula."
        )

    return "\n".join(sources)


def empty_result(message):
    return [message] + [""] * (len(SECTIONS) - 1)


# ==================================================
# ESER ARAŞTIRMASI
# ==================================================

def research_artifact(image_path, extra_info):

    if not API_KEY:
        return empty_result(
            "### API anahtarı bulunamadı\n\n"
            "Render → Environment bölümünde `GEMINI_API_KEY` "
            "değişkeninin tanımlı olduğunu kontrol et."
        )

    if not image_path:
        return empty_result(
            "Lütfen önce araştırmak istediğin eserin fotoğrafını yükle."
        )

    try:
        image_data = prepare_image(image_path)

        details = (extra_info or "").strip()
        if not details:
            details = "Kullanıcı ek bilgi vermedi."

        prompt = f"""
Sen Tarihinİzi uygulamasının tarihî eser araştırma asistanısın.

Kullanıcı tarafından yüklenen görseli incele ve eseri araştır.

Kullanıcının ek bilgisi:
{details}

KURALLAR:
- Görseldeki eserin kimliğini dikkatlice değerlendir.
- Google Arama aracını kullanarak bilgileri doğrulamaya çalış.
- Müze, resmî kültür kurumu, akademik yayın ve güvenilir
  tarih kaynaklarına öncelik ver.
- Eserin kimliği kesin değilse bunu açıkça belirt.
- Tarih, dönem, sanatçı ve konum bilgilerini uydurma.
- Bilinmeyen bilgileri "Doğrulanamadı" olarak yaz.
- Görselde okunmayan yazıları tahmin ederek gerçekmiş gibi sunma.
- Kullanıcıya Türkçe cevap ver.
- Kaynakları ve bağlantıları yalnızca gerçekten doğrulayabildiğinde yaz.

Aşağıdaki anahtarların tamamını içeren geçerli bir JSON nesnesi üret.
JSON dışında açıklama veya Markdown kod bloğu ekleme.
Her anahtarın değeri metin olsun.

Anahtarlar:
{json.dumps(SECTIONS, ensure_ascii=False)}

Bölümler:
Genel Bilgi: Eserin tanımı ve temel özellikleri.
Tarihçe: Bilinen tarihî geçmişi.
Dönem ve Tarih: Yapım tarihi ve tarihsel dönem.
Coğrafi Konum: Bulunduğu yer ve keşif yeri biliniyorsa.
Mimari ve Üslup: Mimari özellikleri veya sanat üslubu.
Malzeme ve Teknik: Kullanılan malzemeler ve yapım tekniği.
Kullanım Amacı: Tarihsel işlevi.
Kültürel Önemi: Kültür ve tarih açısından önemi.
Yazıt ve Semboller: Görülebilen yazılar ve semboller.
Benzer Eserler: Güvenilir biçimde belirlenmiş benzer eserler.
Koruma Durumu: Biliniyorsa güncel koruma durumu.
Eserin Kimliği: Eserin tanımlanmasına ilişkin kanıtlar ve belirsizlikler.
Kaynaklar: Araştırmada kullanılan kaynaklar.
Kısa Özet: Temel bulguların kısa özeti.
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
        print("Gemini isteği gönderiliyor.", flush=True)

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
            response_data = response.json()
        except ValueError:
            response_data = {}

        if not response.ok:
            error = response_data.get("error", {})
            message = error.get(
                "message",
                response.text[:3000] or "Açıklama bulunamadı.",
            )

            print(
                "GEMINI_ERROR_BODY="
                + json.dumps(response_data, ensure_ascii=False)[:5000],
                flush=True,
            )

            if response.status_code == 429:
                return empty_result(
                    "### Gemini API kota hatası (429)\n\n"
                    f"**Model:** `{MODEL}`\n\n"
                    f"**Google'ın hata mesajı:**\n\n{message}\n\n"
                    "Google AI Studio'da doğru projeyi, modelin "
                    "kotasını ve kullanım sınırlarını kontrol et. "
                    "Kod model isteğini 3.5 Flash-Lite adresine "
                    "gönderiyor; ancak Google'ın kotayı kabul "
                    "edeceğini garanti edemez."
                )

            if response.status_code in (401, 403):
                return empty_result(
                    "### API erişim hatası\n\n"
                    f"{message}\n\n"
                    "Render'daki API anahtarını ve bağlı olduğu "
                    "Google projesini kontrol et."
                )

            return empty_result(
                f"### Gemini API hatası ({response.status_code})\n\n"
                f"{message}"
            )

        candidates = response_data.get("candidates", [])

        if not candidates:
            reason = response_data.get(
                "promptFeedback", {}
            ).get("blockReason", "Açıklama yok")

            return empty_result(
                f"Google API kullanılabilir bir cevap döndürmedi.\n\n"
                f"**Açıklama:** {reason}"
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
                "Model metin döndürmedi. Farklı bir fotoğrafla "
                "tekrar deneyebilirsin."
            )

        result = extract_json(response_text)

        outputs = [
            str(result.get(section, "Bu bölüm için bilgi bulunamadı."))
            for section in SECTIONS
        ]

        outputs[12] += (
            "\n\n### Google Arama kaynak bağlantıları\n\n"
            + get_sources(candidate)
        )

        outputs[0] = (
            f"**Araştırma modeli:** `{MODEL}`\n\n"
            + outputs[0]
        )

        print("Gemini isteği başarıyla tamamlandı.", flush=True)

        return outputs

    except requests.Timeout:
        print("GEMINI_ERROR=Timeout", flush=True)
        return empty_result(
            "Google API zamanında cevap vermedi. Biraz bekleyip "
            "yeniden deneyebilirsin."
        )

    except requests.RequestException as exc:
        print(
            f"GEMINI_NETWORK_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            "Google API'ye bağlanılamadı. Render Logs bölümünü "
            "kontrol et."
        )

    except (ValueError, TypeError, KeyError) as exc:
        print(
            f"GEMINI_RESPONSE_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            f"Cevap işlenirken hata oluştu:\n\n{exc}"
        )

    except Exception as exc:
        print(
            f"GEMINI_UNEXPECTED_ERROR={type(exc).__name__}: {exc}",
            flush=True,
        )
        return empty_result(
            "Beklenmeyen bir hata oluştu. Render Logs bölümünü "
            "kontrol et."
        )


# ==================================================
# SADE TASARIM
# ==================================================

CSS = """
.gradio-container {
    max-width: 1150px !important;
    margin: auto !important;
    background: #f5f1e8 !important;
}

body {
    background: #f5f1e8 !important;
}

#main-header {
    background: #782f32 !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    padding: 22px 24px !important;
    margin-bottom: 18px !important;
    text-align: left !important;
    border-bottom: 3px solid #b99a5b !important;
}

#main-header h1 {
    color: #ffffff !important;
    font-size: 30px !important;
    font-weight: 700 !important;
    margin: 0 0 6px 0 !important;
}

#main-header p {
    color: #f2e8dc !important;
    font-size: 14px !important;
    margin: 0 !important;
}

#research-button {
    background: #782f32 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

#research-button:hover {
    background: #632528 !important;
}

button, input, textarea {
    border-radius: 8px !important;
}

footer {
    display: none !important;
}
"""


# ==================================================
# GRADIO ARAYÜZÜ
# ==================================================

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="rose",
        secondary_hue="amber",
        neutral_hue="stone",
    ),
    css=CSS,
    title="Tarihinİzi",
) as demo:

    gr.HTML("""
    <div id="main-header">
        <h1>🇹🇷 Tarihinİzi</h1>
        <p>
            Tarihî eserleri keşfet, geçmişin izlerini sür.
        </p>
    </div>
    """)

    gr.Markdown(
        f"**Aktif model:** `{MODEL}`\n\n"
        "Eser fotoğrafını yükle ve araştırmayı başlat. "
        "Sonuçları ve kaynakları ayrı sekmelerde incele."
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
                "Eseri Araştır",
                variant="primary",
                elem_id="research-button",
            )

        with gr.Column(scale=2):
            result_boxes = []

            with gr.Tabs():
                for section in SECTIONS:
                    with gr.Tab(section):
                        output = gr.Markdown(
                            "Fotoğraf yükledikten sonra "
                            "araştırma sonuçları burada görünür."
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
