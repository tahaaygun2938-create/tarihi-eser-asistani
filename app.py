import os
import json
import base64
import requests
import gradio as gr
from PIL import Image

# =========================================================
# TARIHINIZI - MODEL AYARLARI
# =========================================================

MODEL = "gemini-3.5-flash-lite"

API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or ""
).strip()

API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
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


def empty_result(message):
    """Hata durumunda yalnızca ilk sekmede hata göster."""
    return [message] + [""] * (len(SECTIONS) - 1)


def prepare_image(image_path):
    """Yüklenen görseli Gemini API için JPEG verisine dönüştür."""
    with Image.open(image_path) as original:
        img = original.convert("RGB")
        img.thumbnail((1600, 1600))

        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)

        image_data = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

    return image_data


def extract_response(data):
    """Gemini cevabını güvenli şekilde oku."""
    candidates = data.get("candidates", [])

    if not candidates:
        prompt_feedback = data.get("promptFeedback", {})
        block_reason = prompt_feedback.get("blockReason")

        if block_reason:
            raise ValueError(
                f"Google isteği engelledi. Sebep: {block_reason}"
            )

        raise ValueError(
            "Google API boş cevap döndürdü. Render Logs bölümünü kontrol et."
        )

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])

    text_parts = [
        part.get("text", "")
        for part in parts
        if part.get("text")
    ]

    if not text_parts:
        raise ValueError(
            "Model metin döndürmedi. Lütfen farklı bir eser fotoğrafı dene."
        )

    return "\n".join(text_parts), candidate


def extract_json(text):
    """Modelin JSON cevabını ayrıştır."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])

        raise ValueError(
            "Modelin cevabı beklenen JSON biçiminde değil. "
            "Lütfen tekrar dene."
        )


def extract_sources(candidate):
    """Google Arama sonuçlarından dönen kaynak bağlantılarını al."""
    metadata = candidate.get("groundingMetadata", {})
    chunks = metadata.get("groundingChunks", [])

    sources = []
    seen_urls = set()

    for chunk in chunks:
        web_source = chunk.get("web", {})
        title = web_source.get("title", "Kaynak")
        url = web_source.get("uri", "")

        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(f"- [{title}]({url})")

    if sources:
        return "\n".join(sources)

    return (
        "Google Arama bağlantısı bu yanıtta kaynak döndürmedi. "
        "Eser bilgilerini bağımsız olarak doğrula."
    )


def research_artifact(image_path, extra_info):
    if not API_KEY:
        return empty_result(
            "HATA: API anahtarı bulunamadı.\n\n"
            "Render → Environment bölümüne `GEMINI_API_KEY` "
            "adında bir değişken ekle ve değerine Google AI Studio "
            "API anahtarını yaz. Anahtarı kodun içine koyma."
        )

    if not image_path:
        return empty_result("Lütfen önce bir tarihî eser fotoğrafı yükle.")

    try:
        image_data = prepare_image(image_path)

        user_details = (extra_info or "").strip()
        if not user_details:
            user_details = "Kullanıcı ek bilgi vermedi."

        prompt = f"""
Sen Tarihinİzi adlı tarihî eser araştırma uygulamasının uzman
araştırma asistanısın. Kullanıcı tarafından yüklenen görseli incele.

KULLANICININ EK BİLGİSİ:
{user_details}

GÖREV:
1. Görseldeki eserin ne olabileceğini belirle.
2. Google Arama aracını kullanarak bilgileri güvenilir kaynaklarla
   karşılaştır. Mümkünse müze, resmî kültür kurumu, kazı raporu,
   akademik yayın veya güvenilir ansiklopedi kaynaklarına öncelik ver.
3. Eserin kimliği kesin değilse bunu açıkça söyle. Tahmini bilgiyi
   kesin tarihî gerçek gibi sunma.
4. Fotoğrafta görülemeyen yazıları veya ayrıntıları uydurma.
5. Bulamadığın bilgileri "Doğrulanamadı" şeklinde belirt.
6. Görseldeki eser ile internette bulduğun eser arasında uyuşmazlık
   varsa bunu özellikle açıkla.
7. Yanıtı Türkçe yaz.
8. Aşağıdaki anahtarları içeren, geçerli bir JSON nesnesi döndür.
   JSON dışında açıklama veya Markdown kod çiti yazma.
9. Her anahtarın değeri bir metin olmalı.

JSON anahtarları:
{json.dumps(SECTIONS, ensure_ascii=False)}

Her bölümde olabildiğince açıklayıcı ol. Kaynaklar bölümünde
kaynak adlarını ve bağlantılarını belirt. Google Arama sonuçları
kaynak döndürmezse bunu açıkça belirt; bağlantı uydurma.
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
                "responseMimeType": "application/json",
                "maxOutputTokens": 7000,
            },
        }

        # Model adı ekranda da gösterilen MODEL sabitinden geliyor.
        print(f"TARIHINIZI_MODEL={MODEL}")
        print("Gemini API isteği gönderiliyor.")

        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY,
            },
            json=payload,
            timeout=120,
        )

        # Hata cevabını kaybetmeden işle.
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}

        if not response.ok:
            error_info = response_data.get("error", {})
            error_message = error_info.get(
                "message",
                response.text[:1500] or "Açıklama bulunamadı.",
            )
            status = response.status_code

            print(f"GEMINI_HTTP_STATUS={status}")
            print(f"GEMINI_ERROR={error_message[:1500]}")

            if status == 429:
                return empty_result(
                    "GEMINI KOTA HATASI (429)\n\n"
                    f"Google'ın mesajı:\n{error_message}\n\n"
                    "Model isteği: gemini-3.5-flash-lite\n\n"
                    "Kontrol et:\n"
                    "1. Google AI Studio'da doğru projeyi seç.\n"
                    "2. Usage bölümünde 3.5 Flash-Lite kullanımını kontrol et.\n"
                    "3. Rate limits bölümündeki aktif RPM, TPM ve günlük "
                    "istek limitlerini kontrol et.\n"
                    "4. Render'daki GEMINI_API_KEY değerinin, kontrol "
                    "ettiğin projeye ait olduğundan emin ol.\n\n"
                    "Not: Kod, Google'ın kota sınırını kaldıramaz."
                )

            if status in (401, 403):
                return empty_result(
                    f"API ERİŞİM HATASI ({status})\n\n"
                    f"Google'ın mesajı:\n{error_message}\n\n"
                    "Render → Environment bölümündeki API anahtarını ve "
                    "anahtarın bağlı olduğu Google projesini kontrol et."
                )

            if status == 404:
                return empty_result(
                    "MODEL BULUNAMADI (404)\n\n"
                    f"Google'ın mesajı:\n{error_message}\n\n"
                    f"İstek yapılan model: {MODEL}"
                )

            return empty_result(
                f"GEMINI API HATASI ({status})\n\n{error_message}"
            )

        response_text, candidate = extract_response(response_data)
        result = extract_json(response_text)

        outputs = [
            str(result.get(section, "Bu bölüm için bilgi bulunamadı."))
            for section in SECTIONS
        ]

        # Kaynaklar sekmesini API'nin gerçek kaynaklarıyla destekle.
        actual_sources = extract_sources(candidate)
        existing_sources = outputs[12].strip()

        outputs[12] = (
            existing_sources
            + "\n\n### Google Arama kaynak bağlantıları\n"
            + actual_sources
        ).strip()

        # Modeli görünür şekilde belirt.
        outputs[0] = (
            f"**Kullanılan model:** `{MODEL}`\n\n"
            + outputs[0]
        )

        print("Gemini API isteği başarıyla tamamlandı.")
        return outputs

    except requests.Timeout:
        return empty_result(
            "ZAMAN AŞIMI: Google API zamanında cevap vermedi. "
            "Biraz bekleyip tekrar dene."
        )

    except requests.RequestException as exc:
        print(f"NETWORK_ERROR={type(exc).__name__}: {exc}")
        return empty_result(
            "BAĞLANTI HATASI: Google API'ye ulaşılamadı. "
            "Render Logs bölümünü kontrol et."
        )

    except (ValueError, KeyError, TypeError) as exc:
        print(f"RESPONSE_ERROR={type(exc).__name__}: {exc}")
        return empty_result(
            f"CEVAP İŞLEME HATASI: {exc}\n\n"
            "Render Logs bölümünde ayrıntılar bulunabilir."
        )

    except Exception as exc:
        print(f"UNEXPECTED_ERROR={type(exc).__name__}: {exc}")
        return empty_result(
            "Beklenmeyen bir hata oluştu. Render Logs bölümünü kontrol et."
        )


# =========================================================
# ARAYÜZ
# =========================================================

CSS = """
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}
#main-header {
    background: linear-gradient(135deg, #780000, #c1121f, #e63946);
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 26px;
    margin-bottom: 18px;
    text-align: center;
}
#main-header h1, #main-header p {
    color: #ffffff !important;
}
#main-header h1 {
    font-size: 36px !important;
    font-weight: 900 !important;
    margin-bottom: 8px !important;
}
#main-header p {
    font-size: 15px !important;
}
#research-button {
    background: linear-gradient(90deg, #b00020, #e63946) !important;
    color: white !important;
    border: none !important;
    font-weight: 800 !important;
}
"""

with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="amber",
    ),
    css=CSS,
    title="Tarihinİzi",
) as demo:

    gr.HTML("""
    <div id="main-header">
        <h1>🇹🇷 Tarihinİzi</h1>
        <p>
            Geçmişin izlerini keşfet.
            Tarihî eserleri görsellerle araştır,
            bilgileri kaynaklarla karşılaştır.
        </p>
    </div>
    """)

    gr.Markdown(
        f"**Aktif model:** `{MODEL}`  \n"
        "Araştırma sonuçları yapay zekâ tarafından hazırlanır. "
        "Önemli tarihî bilgileri kaynaklardan doğrula."
    )

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label="Tarihî eser fotoğrafı",
                type="filepath",
                height=330,
            )

            extra_info = gr.Textbox(
                label="Ek bilgi (isteğe bağlı)",
                placeholder=(
                    "Örneğin: Bulunduğu şehir, köy, müze veya "
                    "eser üzerindeki yazılar..."
                ),
                lines=3,
            )

            research_button = gr.Button(
                "🔎 Eseri Araştır",
                variant="primary",
                elem_id="research-button",
            )

            gr.Markdown(
                "İpucu: Eserin tamamının ve üzerindeki yazıların "
                "net göründüğü bir fotoğraf yükle."
            )

        with gr.Column(scale=2):
            result_boxes = []

            with gr.Tabs():
                for section in SECTIONS:
                    with gr.Tab(section):
                        output = gr.Markdown(
                            value="Araştırma başlatıldığında sonuç burada görünür."
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
    demo.queue(default_concurrency_limit=2).launch(
        server_name="0.0.0.0",
        server_port=port,
    )
