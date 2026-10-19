
import os
import json
import base64
import requests
import gradio as gr
from io import BytesIO

# ==============================
# AYARLAR
# ==============================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    + MODEL
    + ":generateContent"
)

# ==============================
# ESKİ SADE TÜRK TEMASI
# ==============================

CSS = """
body, .gradio-container {
    background: #f4f1eb !important;
    color: #222 !important;
}

.gradio-container {
    max-width: 1050px !important;
    margin: auto !important;
}

#baslik {
    background: #b5121b;
    color: white;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    margin-bottom: 12px;
}

#baslik h1 {
    font-size: 30px;
    font-weight: 700;
    margin: 0;
}

#baslik p {
    margin: 8px 0 0 0;
    font-size: 14px;
}

#ana-panel {
    background: #ffffff;
    border: 1px solid #ded5c8;
    border-radius: 8px;
    padding: 12px;
}

button.primary {
    background: #b5121b !important;
    color: white !important;
    border: none !important;
}

button.primary:hover {
    background: #8f0d15 !important;
}

.tab-nav button.selected {
    color: #b5121b !important;
    border-color: #b5121b !important;
}

footer {
    display: none !important;
}
"""

HEADER = """
<div id="baslik">
    <div style="font-size:34px;">🇹🇷</div>
    <h1>TARİHİNİZİ</h1>
    <p>Geçmişin izlerini keşfet.</p>
</div>
"""

# ==============================
# AYRINTILI ESER ANALİZİ
# ==============================

PROMPT = """
Sen tarih, arkeoloji, sanat tarihi, epigrafi ve kültürel miras
alanlarında uzman bir araştırma asistanısın.

Yüklenen görseldeki tarihî eseri mümkün olduğunca ayrıntılı incele.
Yanıtın tamamen Türkçe olsun.

KURALLAR:
1. Görselde olmayan bilgileri kesin gerçekmiş gibi yazma.
2. Eserin kimliğinden emin değilsen olası kimlikleri ve gerekçelerini belirt.
3. Tahminleri doğrulanmış bilgilerden açıkça ayır.
4. Kesin kazı yeri, tarih, üretici, müze envanter numarası veya kaynak uydurma.
5. Görseldeki yazı, motif, figür, sembol ve fiziksel özellikleri ayrı ayrı incele.
6. Görselden anlaşılamayan boyut veya malzeme hakkında kesin hüküm verme.
7. Belirli bir kaynak doğrulanamıyorsa bunu açıkça yaz.
8. Sadece genel bilgiler değil, yüklenen görsele özgü gözlemler sun.
9. Bilgileri ayrıntılı ama anlaşılır anlat.
10. Bir eserin gerçekliğini yalnızca fotoğrafa bakarak kesinleştirme.

Aşağıdaki JSON alanlarını eksiksiz doldurmaya çalış:

{
  "kimlik": "Eserin adı veya olası tanımı",
  "guven": "Kimlik tespitinin güven düzeyi ve gerekçesi",
  "ozet": "Eserin ayrıntılı genel tanıtımı",
  "fiziksel": "Görselde gözlemlenen biçim, renk, malzeme izleri ve yapı",
  "donem": "Olası tarih ve dönem, tarihlendirme gerekçesi",
  "medeniyet": "Olası medeniyet ve kültürel çevre",
  "cografya": "Olası coğrafi köken ve belirsizlikler",
  "yapim": "Üretim tekniği ve işçilik hakkında değerlendirme",
  "sanat": "Sanat üslubu, bezeme, motif ve kompozisyon",
  "semboller": "Sembollerin olası anlamları",
  "yazi": "Yazıtlar, alfabe ve okunabilen metinler",
  "amac": "Muhtemel kullanım amacı",
  "toplum": "Eserin dönemin toplumsal hayatıyla ilişkisi",
  "din": "Varsa dinî veya törensel bağlam; kanıt yoksa belirt",
  "siyaset": "Varsa siyasi, askerî veya yönetimsel bağlam",
  "ekonomi": "Üretim, ticaret veya ekonomik hayatla muhtemel ilişkisi",
  "tarih": "Eserin tarihsel bağlamı ve önemi",
  "arkeoloji": "Arkeolojik açıdan değerlendirme",
  "benzerlikler": "Benzer eserlerle karşılaştırma",
  "korunma": "Fotoğrafta gözlemlenebilen korunma durumu",
  "belirsizlik": "Tespit edilemeyen noktalar",
  "dogrulama": "Kimliği doğrulamak için gereken ek kanıtlar",
  "kaynaklar": "Araştırmada başvurulabilecek gerçek kurum ve kataloglar"
}

Kaynaklar bölümünde doğrulanmamış bağlantı üretme.
Her alanı mümkün olduğunca ayrıntılı yaz; kanıt yoksa açıkça belirt.
JSON dışında açıklama ekleme.
"""

# ==============================
# GÖRSEL HAZIRLAMA
# ==============================

def prepare_image(image):
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def read_response(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end < start:
        raise ValueError("Yapay zekâ geçerli bir JSON yanıtı döndürmedi.")

    return json.loads(text[start:end + 1])


# ==============================
# BİLGİLERİ DÜZENLE
# ==============================

def section(title, value):
    value = str(value or "Bu konuda yeterli bilgi belirlenemedi.")
    return f"## {title}\n\n{value}"


def format_sources(value):
    if isinstance(value, str):
        return value or "Kesin kaynak kaydı doğrulanamadı."

    if isinstance(value, list):
        result = []

        for item in value:
            if isinstance(item, dict):
                name = item.get("ad", "Kaynak")
                detail = item.get("aciklama", item.get("amac", ""))
                result.append(f"### {name}\n{detail}")
            else:
                result.append(str(item))

        return "\n\n".join(result) or "Kesin kaynak kaydı doğrulanamadı."

    return "Kaynaklar ayrıca doğrulanmalıdır."


# ==============================
# ESERİ ANALİZ ET
# ==============================

def analyze(image, extra):
    error_outputs = ("", "", "", "", "", "", "", "")

    if image is None:
        return (
            "Önce bir eser fotoğrafı yükle.",
            *error_outputs[1:]
        )

    if not API_KEY:
        return (
            "API anahtarı bulunamadı. Render Environment bölümünde "
            "GEMINI_API_KEY değişkenini kontrol et.",
            *error_outputs[1:]
        )

    try:
        encoded = prepare_image(image)

        extra = (extra or "").strip()
        if not extra:
            extra = "Kullanıcı ek bilgi vermedi."

        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": PROMPT
                        + "\n\nKullanıcının verdiği ek bilgi:\n"
                        + extra
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded
                        }
                    }
                ]
            }],
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
                f"API hatası: HTTP {response.status_code}\n\n{detail}",
                *error_outputs[1:]
            )

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            return (
                "Yapay zekâ yanıt üretmedi. API kotasını ve model erişimini kontrol et.",
                *error_outputs[1:]
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        answer = "\n".join(
            part.get("text", "") for part in parts if part.get("text")
        )

        result = read_response(answer)

        identity = (
            f"# {result.get('kimlik', 'Eser belirlenemedi')}\n\n"
            f"**Güven düzeyi:** {result.get('guven', 'Belirtilmedi')}\n\n"
            f"{result.get('ozet', '')}"
        )

        physical = "\n\n".join([
            section("Fiziksel özellikler", result.get("fiziksel")),
            section("Yapım tekniği ve işçilik", result.get("yapim")),
            section("Sanatsal özellikler", result.get("sanat")),
            section("Semboller ve motifler", result.get("semboller")),
            section("Yazıt ve alfabe", result.get("yazi"))
        ])

        history = "\n\n".join([
            section("Tarih ve dönem", result.get("donem")),
            section("Medeniyet", result.get("medeniyet")),
            section("Coğrafi köken", result.get("cografya")),
            section("Tarihsel bağlam", result.get("tarih")),
            section("Toplumsal hayat", result.get("toplum"))
        ])

        context = "\n\n".join([
            section("Kullanım amacı", result.get("amac")),
            section("Dinî ve törensel bağlam", result.get("din")),
            section("Siyasi ve askerî bağlam", result.get("siyaset")),
            section("Ekonomik hayatla ilişkisi", result.get("ekonomi"))
        ])

        archaeology = "\n\n".join([
            section("Arkeolojik değerlendirme", result.get("arkeoloji")),
            section("Benzer eserler", result.get("benzerlikler")),
            section("Korunma durumu", result.get("korunma"))
        ])

        verification = "\n\n".join([
            section("Belirsizlikler", result.get("belirsizlik")),
            section("Doğrulama yolları", result.get("dogrulama"))
        ])

        sources = format_sources(result.get("kaynaklar"))

        status = (
            "Analiz tamamlandı. Bu değerlendirme fotoğrafa dayalıdır; "
            "kesin eser kimliği ve tarih için uzman incelemesi veya "
            "güvenilir katalog kaydı gerekebilir."
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
        return (
            "İstek zaman aşımına uğradı. Biraz sonra tekrar dene.",
            *error_outputs[1:]
        )

    except requests.exceptions.RequestException as exc:
        return (
            f"Bağlantı hatası: {exc}",
            *error_outputs[1:]
        )

    except (ValueError, json.JSONDecodeError) as exc:
        return (
            f"Yanıt okunamadı: {exc}",
            *error_outputs[1:]
        )

    except Exception as exc:
        return (
            f"Beklenmeyen hata ({type(exc).__name__}): {exc}",
            *error_outputs[1:]
        )


# ==============================
# UYGULAMA ARAYÜZÜ
# ==============================

with gr.Blocks(
    title="Tarihinİzi",
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="gray",
        neutral_hue="stone"
    ),
    css=CSS
) as app:

    gr.HTML(HEADER)

    gr.Markdown(
        "Yüklediğin tarihî eseri incele; kökeni, tarihi, "
        "kullanımı ve kültürel önemine dair ayrıntılı bir analiz al."
    )

    with gr.Group(elem_id="ana-panel"):
        image_input = gr.Image(
            label="Eser fotoğrafı",
            type="pil",
            height=300
        )

        extra_input = gr.Textbox(
            label="Ek bilgi (isteğe bağlı)",
            placeholder="Örneğin: Bulunduğu yer, üzerindeki yazı veya bilinen adı",
            lines=2
        )

        with gr.Row():
            analyze_button = gr.Button(
                "🇹🇷 Eseri İncele",
                variant="primary"
            )
            clear_button = gr.Button("Temizle")

    with gr.Accordion("Analiz Sonuçları", open=True):
        out_identity = gr.Markdown()

    with gr.Tabs():
        with gr.Tab("Fiziksel ve Sanatsal"):
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

    out_status = gr.Markdown("🇹🇷 Hazır.")

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
        fn=analyze,
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
