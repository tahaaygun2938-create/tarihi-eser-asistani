
import os
import json
import base64
import requests
import gradio as gr
from io import BytesIO

# ==========================================
# AYARLAR
# ==========================================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

# ==========================================
# SADE KOYU TEMA
# ==========================================

CSS = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
}

#main-title {
    text-align: center;
    padding: 12px 0 20px 0;
}

#main-title h1 {
    font-size: 29px;
    font-weight: 600;
    margin-bottom: 6px;
}

#main-title p {
    color: #aaaaaa;
    font-size: 14px;
}

footer {
    display: none !important;
}
"""

HEADER = """
<div id="main-title">
    <h1>🇹🇷 Tarihinİzi</h1>
    <p>Tarihî eserleri keşfet, geçmişin izini sür.</p>
</div>
"""

# ==========================================
# ESER ANALİZ TALİMATI
# ==========================================

PROMPT = """
Sen tarih, arkeoloji, sanat tarihi ve kültürel miras
alanlarında uzman bir araştırma asistanısın.

Kullanıcının yüklediği görseli ayrıntılı olarak incele.
Yanıtı Türkçe hazırla ve yalnızca geçerli JSON döndür.

ÖNEMLİ KURALLAR:
- Görselde olmayan ayrıntıları uydurma.
- Kimlik tespiti kesin değilse olası seçenekleri belirt.
- Tahminleri doğrulanmış bilgilerden ayır.
- Kesin tarih, buluntu yeri, müze numarası veya kaynak uydurma.
- Görseldeki yazıları ve sembolleri yalnızca seçilebildikleri ölçüde yorumla.
- Görselden anlaşılamayan boyut ve malzeme hakkında kesin konuşma.
- Bilgi eksikse bunu açıkça yaz.
- Genel bilgiler vermekle yetinme; görseldeki ayrıntıları da değerlendir.
- Kaynaklar gerçek ve ilgili kurumlar olmalı. Belirli bir kayıt
  doğrulanmadıysa bunu açıkça belirt.
- Fotoğrafa bakarak eserin orijinalliğini kesinleştirme.

Aşağıdaki alanları içeren JSON nesnesi döndür:

{
  "kimlik": "Eserin adı veya olası tanımı",
  "guven": "Kimlik tespitinin güven düzeyi ve gerekçesi",
  "ozet": "Eserin ayrıntılı tanıtımı",
  "fiziksel": "Görseldeki biçim, renk, yüzey ve malzeme izleri",
  "donem": "Olası dönem ve tarihlendirme gerekçesi",
  "medeniyet": "Olası medeniyet ve kültürel çevre",
  "cografya": "Olası coğrafi köken ve belirsizlikler",
  "yapim": "Üretim tekniği ve işçilik",
  "sanat": "Sanat üslubu, motifler, bezemeler ve kompozisyon",
  "semboller": "Semboller ve olası anlamları",
  "yazi": "Yazıtlar, alfabe ve okunabilen metin",
  "amac": "Muhtemel kullanım amacı",
  "toplum": "Toplumsal hayatla ilişkisi",
  "din": "Varsa dinî veya törensel bağlam",
  "siyaset": "Varsa siyasi veya askerî bağlam",
  "ekonomi": "Ticaret ve ekonomik hayatla ilişkisi",
  "tarih": "Tarihsel bağlam ve önemi",
  "arkeoloji": "Arkeolojik açıdan değerlendirme",
  "benzerlikler": "Benzer eserlerle karşılaştırma",
  "korunma": "Fotoğrafta görülebilen korunma durumu",
  "belirsizlik": "Kesin olarak belirlenemeyen noktalar",
  "dogrulama": "Kimliği doğrulamak için gereken ek kanıtlar",
  "kaynaklar": [
    {
      "ad": "Kurum veya katalog adı",
      "adres": "Bilinen resmî adres; bilinmiyorsa boş bırak",
      "aciklama": "Kaynağın hangi bilgiyi doğrulayabileceği"
    }
  ]
}

JSON dışında metin yazma.
"""

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================

def encode_image(image):
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("JSON yanıtı bulunamadı.")

    return json.loads(text[start:end + 1])


def show_section(title, value):
    value = str(value or "Bu konuda yeterli bilgi belirlenemedi.")
    return f"## {title}\n\n{value}"


def format_sources(sources):
    if isinstance(sources, str):
        return sources or "Doğrulanmış kaynak bilgisi bulunamadı."

    if not isinstance(sources, list) or not sources:
        return "Doğrulanmış kaynak bilgisi bulunamadı."

    result = []

    for source in sources:
        if isinstance(source, dict):
            name = source.get("ad", "Kaynak")
            description = source.get("aciklama", "")
            address = str(source.get("adres", "")).strip()

            item = f"### {name}\n\n{description}"

            if address.startswith(("https://", "http://")):
                item += f"\n\n[Kaynağı aç]({address})"

            result.append(item)
        else:
            result.append(str(source))

    return "\n\n".join(result)


# ==========================================
# ANALİZ
# ==========================================

def analyze_artifact(image, extra_info):
    empty = ("", "", "", "", "", "", "", "")

    if image is None:
        return ("Önce bir eser fotoğrafı yükle.",) + empty[1:]

    if not API_KEY:
        return (
            "API anahtarı bulunamadı. Render Environment bölümünde "
            "GEMINI_API_KEY değişkenini tanımlamalısın."
        ) + empty[1:]

    try:
        encoded = encode_image(image)

        extra_info = (extra_info or "").strip()
        if not extra_info:
            extra_info = "Ek bilgi verilmedi."

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                PROMPT
                                + "\n\nKullanıcının ek bilgisi:\n"
                                + extra_info
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": encoded
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 5000
            }
        }

        response = requests.post(
            API_URL,
            params={"key": API_KEY},
            json=payload,
            timeout=90
        )

        if response.status_code != 200:
            try:
                detail = response.json().get("error", {}).get(
                    "message", response.text[:500]
                )
            except Exception:
                detail = response.text[:500]

            return (
                f"**API hatası: HTTP {response.status_code}**\n\n{detail}"
            ) + empty[1:]

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            return (
                "Model yanıt üretmedi. API kotasını ve model erişimini kontrol et."
            ) + empty[1:]

        parts = candidates[0].get("content", {}).get("parts", [])
        answer = "\n".join(
            part.get("text", "")
            for part in parts
            if part.get("text")
        )

        if not answer:
            return ("Model boş yanıt döndürdü. Tekrar dene.",) + empty[1:]

        result = parse_json(answer)

        identity = (
            f"# {result.get('kimlik', 'Eser belirlenemedi')}\n\n"
            f"**Güven düzeyi:** {result.get('guven', 'Belirtilmedi')}\n\n"
            f"{result.get('ozet', '')}"
        )

        physical = "\n\n".join([
            show_section("Fiziksel özellikler", result.get("fiziksel")),
            show_section("Üretim ve işçilik", result.get("yapim")),
            show_section("Sanat ve bezeme", result.get("sanat")),
            show_section("Semboller", result.get("semboller")),
            show_section("Yazıtlar", result.get("yazi"))
        ])

        history = "\n\n".join([
            show_section("Dönem ve tarihlendirme", result.get("donem")),
            show_section("Medeniyet", result.get("medeniyet")),
            show_section("Coğrafi köken", result.get("cografya")),
            show_section("Tarihsel önem", result.get("tarih"))
        ])

        context = "\n\n".join([
            show_section("Kullanım amacı", result.get("amac")),
            show_section("Toplumsal hayat", result.get("toplum")),
            show_section("Dinî bağlam", result.get("din")),
            show_section("Siyasi ve askerî bağlam", result.get("siyaset")),
            show_section("Ekonomik bağlam", result.get("ekonomi"))
        ])

        archaeology = "\n\n".join([
            show_section("Arkeolojik değerlendirme", result.get("arkeoloji")),
            show_section("Benzer eserler", result.get("benzerlikler")),
            show_section("Korunma durumu", result.get("korunma"))
        ])

        verification = "\n\n".join([
            show_section("Belirsizlikler", result.get("belirsizlik")),
            show_section("Doğrulama yolları", result.get("dogrulama"))
        ])

        sources = format_sources(result.get("kaynaklar"))

        status = (
            "Analiz tamamlandı. Sonuçlar görselden üretilmiş ön "
            "değerlendirmelerdir; kesin kimlik için güvenilir katalog "
            "veya uzman incelemesi gerekebilir."
        )

        return (
            identity,
            physical,
            history,
            context,
            archaeology,
            verification,
            sources,
            status
        )

    except requests.exceptions.Timeout:
        return ("İstek zaman aşımına uğradı. Tekrar dene.",) + empty[1:]

    except requests.exceptions.RequestException as error:
        return (f"Bağlantı hatası: {error}",) + empty[1:]

    except (ValueError, json.JSONDecodeError) as error:
        return (f"Yanıt okunamadı: {error}",) + empty[1:]

    except Exception as error:
        return (
            f"Beklenmeyen hata ({type(error).__name__}): {error}"
        ) + empty[1:]


# ==========================================
# ARAYÜZ
# ==========================================

with gr.Blocks(
    title="Tarihinİzi",
    theme=gr.themes.Base(
        primary_hue="gray",
        neutral_hue="slate"
    ),
    css=CSS
) as app:

    gr.HTML(HEADER)

    gr.Markdown(
        "Bir tarihî eser görseli yükle ve eser hakkında ayrıntılı bilgi edin."
    )

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label="Eser fotoğrafı",
                type="pil",
                height=300
            )

            extra_input = gr.Textbox(
                label="Ek bilgi (isteğe bağlı)",
                placeholder="Eserin bulunduğu yer veya bildiğin diğer bilgiler...",
                lines=3
            )

            analyze_button = gr.Button(
                "Eseri İncele",
                variant="primary"
            )

            clear_button = gr.Button("Temizle")

        with gr.Column(scale=2):
            out_identity = gr.Markdown()

            with gr.Tabs():
                with gr.Tab("Fiziksel Özellikler"):
                    out_physical = gr.Markdown()

                with gr.Tab("Tarih ve Medeniyet"):
                    out_history = gr.Markdown()

                with gr.Tab("Toplumsal Bağlam"):
                    out_context = gr.Markdown()

                with gr.Tab("Arkeoloji"):
                    out_archaeology = gr.Markdown()

                with gr.Tab("Doğrulama"):
                    out_verification = gr.Markdown()

                with gr.Tab("Kaynaklar"):
                    out_sources = gr.Markdown()

    out_status = gr.Markdown("Hazır.")

    outputs = [
        out_identity,
        out_physical,
        out_history,
        out_context,
        out_archaeology,
        out_verification,
        out_sources,
        out_status
    ]

    analyze_button.click(
        fn=analyze_artifact,
        inputs=[image_input, extra_input],
        outputs=outputs
    )

    clear_button.click(
        fn=lambda: (None, "", "", "", "", "", "", "", "", ""),
        inputs=[],
        outputs=[
            image_input,
            extra_input,
            out_identity,
            out_physical,
            out_history,
            out_context,
            out_archaeology,
            out_verification,
            out_sources,
            out_status
        ]
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    app.queue().launch(
        server_name="0.0.0.0",
        server_port=port
    )
