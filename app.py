
import os
import json
import base64
import requests
import gradio as gr
from PIL import Image
from io import BytesIO

# =========================
# AYARLAR
# =========================

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

# =========================
# TASARIM
# =========================

CSS = """
.gradio-container {
    max-width: 1150px !important;
    margin: auto !important;
    background: #f5f5f5;
}
#header {
    background: linear-gradient(135deg, #a80000, #e31b23);
    color: white;
    padding: 28px 20px;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 18px;
}
#header h1 {
    font-size: 35px;
    margin: 0 0 10px 0;
}
#header p {
    font-size: 15px;
    margin: 0;
}
.section {
    border: 1px solid #e5caca;
    border-radius: 12px;
    padding: 15px;
    background: white;
}
button.primary {
    background: #c90016 !important;
    border: none !important;
}
footer {
    display: none !important;
}
"""

HEADER = """
<div id="header">
    <div style="font-size:42px;">🇹🇷</div>
    <h1>TARİHİNİZİ DEĞİL, TARİHİN İZİNİ SÜR</h1>
    <p>Yapay zekâ destekli tarihî eser tanıma ve araştırma platformu</p>
</div>
"""

# =========================
# ANALİZ TALİMATI
# =========================

PROMPT = """
Sen tarih, arkeoloji, sanat tarihi, epigrafi ve kültürel miras
konularında çalışan dikkatli bir araştırma asistanısın.

Kullanıcının yüklediği görseldeki nesneyi Türkçe olarak incele.

ÖNEMLİ KURALLAR:
- Görselde olmayan ayrıntıları uydurma.
- Eserin kimliği kesin değilse bunu açıkça söyle.
- Görselden kesin tarih, üretici, kazı yeri veya müze bilgisi çıkarılamıyorsa
  bunları kesin gerçek gibi sunma.
- Tahmin ile doğrulanmış bilgiyi birbirinden ayır.
- Eserin üzerindeki yazıları yalnızca okunabildiği ölçüde aktar.
- Birden fazla olasılık varsa bunları sırala ve gerekçelendir.
- Bilmediğin kaynakları veya belge numaralarını uydurma.
- Kullanıcının yüklediği görseli incele; yalnızca genel tarih bilgisi verme.
- Sonuçları Türkçe ve ayrıntılı hazırla.

Aşağıdaki alanları içeren geçerli bir JSON nesnesi döndür.
JSON dışında hiçbir metin yazma.

{
  "kimlik": "Eserin olası adı ve tanımı",
  "guven": "Yüksek, orta veya düşük; gerekçesiyle",
  "ozet": "Eserin kısa tanıtımı",
  "fiziksel": "Malzeme, biçim, renk, boyut hakkında görselden anlaşılabilenler",
  "tarih": "Olası dönem ve tarihlendirme gerekçesi",
  "medeniyet": "Olası kültür veya medeniyet ve gerekçesi",
  "cografi": "Olası köken veya coğrafya; belirsizlikleriyle",
  "amac": "Muhtemel kullanım amacı",
  "sanat": "Üslup, motif, işçilik ve süsleme özellikleri",
  "yazi": "Varsa yazıt veya semboller; okunamıyorsa bunu belirt",
  "tarihsel_baglam": "Dönemin tarihsel koşulları ve eserin olası önemi",
  "arkeoloji": "Arkeolojik açıdan değerlendirme ve gerekli ek kanıtlar",
  "karsilastirma": "Benzer eserlerle karşılaştırma; emin değilsen bunu belirt",
  "korunma": "Görselde görülebilen aşınma veya hasar; yalnızca gözlemlenebilenler",
  "belirsizlikler": "Kimlik tespitini zorlaştıran unsurlar",
  "dogrulama": "Kimliği doğrulamak için gereken bilgiler ve incelemeler",
  "kaynaklar": [
    {
      "ad": "Başvurulabilecek gerçek kurum veya katalog",
      "adres": "Bilinen resmî internet adresi veya boş metin",
      "amac": "Bu kaynağın hangi bilgiyi doğrulayabileceği"
    }
  ]
}

Kaynaklar alanında uydurma yayın, bağlantı veya eser kaydı verme.
Belirli esere ait doğrulanmış bir kayıt bilmiyorsan bunu açıkça belirt.
"""
    
# =========================
# YARDIMCI FONKSİYONLAR
# =========================

def image_to_base64(image):
    """PIL görselini API için Base64 biçimine dönüştürür."""
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_json(text):
    """Model yanıtından JSON nesnesini ayıklar."""
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

    if start == -1 or end == -1 or end < start:
        raise ValueError("Model geçerli bir JSON sonucu döndürmedi.")

    return json.loads(text[start:end + 1])


def format_sources(sources):
    if not isinstance(sources, list) or not sources:
        return (
            "Bu analiz sırasında belirli bir eser kaydı doğrulanmadı. "
            "Müze kataloglarından ve akademik kaynaklardan ayrıca kontrol edin."
        )

    output = []
    for item in sources:
        if not isinstance(item, dict):
            continue

        name = str(item.get("ad", "Kaynak belirtilmemiş"))
        purpose = str(item.get("amac", ""))
        address = str(item.get("adres", "")).strip()

        line = f"### {name}\n{purpose}"
        if address.startswith("https://") or address.startswith("http://"):
            line += f"\n\n[Kaynağı aç]({address})"
        output.append(line)

    return "\n\n".join(output) or "Doğrulanmış kaynak kaydı bulunamadı."


# =========================
# ANA ANALİZ FONKSİYONU
# =========================

def analyze_artifact(image, extra_info):
    if image is None:
        return ("Lütfen önce bir görsel yükle.",) * 7

    if not API_KEY:
        message = (
            "## API anahtarı bulunamadı\n\n"
            "Render panelinde **Environment** bölümüne girip "
            "`GEMINI_API_KEY` adında bir ortam değişkeni oluştur. "
            "Değer kısmına Google AI Studio'dan aldığın API anahtarını "
            "yaz ve servisi yeniden dağıt."
        )
        return (message,) * 7

    try:
        encoded_image = image_to_base64(image)

        user_context = (extra_info or "").strip()
        if not user_context:
            user_context = "Kullanıcı ek bilgi vermedi."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": PROMPT + "\n\nKullanıcının ek bilgisi:\n" + user_context},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": encoded_image
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
            detail = ""
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = response.text[:500]

            if response.status_code == 400:
                problem = "İstek geçersiz. Görseli veya model ayarını kontrol et."
            elif response.status_code == 401 or response.status_code == 403:
                problem = "API anahtarı geçersiz olabilir veya bu modele erişim iznin olmayabilir."
            elif response.status_code == 404:
                problem = f"Model bulunamadı: {MODEL}. Render'daki GEMINI_MODEL ayarını kontrol et."
            elif response.status_code == 429:
                problem = "API kullanım kotası dolmuş olabilir. Google AI Studio'daki kotanı kontrol et."
            else:
                problem = f"Google API HTTP {response.status_code} hatası döndürdü."

            message = f"## Analiz yapılamadı\n\n{problem}\n\n**Ayrıntı:** {detail}"
            return (message,) * 7

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            feedback = data.get("promptFeedback", {})
            reason = feedback.get("blockReason", "Model yanıt üretmedi.")
            message = f"## Sonuç alınamadı\n\n{reason}"
            return (message,) * 7

        parts = candidates[0].get("content", {}).get("parts", [])
        answer = "\n".join(
            part.get("text", "") for part in parts if part.get("text")
        ).strip()

        if not answer:
            message = "## Boş yanıt\n\nModel boş bir yanıt döndürdü. Tekrar deneyebilirsin."
            return (message,) * 7

        result = extract_json(answer)

        identity = (
            f"# {result.get('kimlik', 'Eser kimliği belirlenemedi')}\n\n"
            f"**Güven düzeyi:** {result.get('guven', 'Belirtilmedi')}\n\n"
            f"{result.get('ozet', '')}"
        )

        physical = (
            "## Fiziksel özellikler\n\n"
            f"{result.get('fiziksel', '')}\n\n"
            "## Sanatsal özellikler\n\n"
            f"{result.get('sanat', '')}\n\n"
            "## Yazıtlar ve semboller\n\n"
            f"{result.get('yazi', '')}"
        )

        history = (
            "## Tarihlendirme\n\n"
            f"{result.get('tarih', '')}\n\n"
            "## Medeniyet ve coğrafya\n\n"
            f"{result.get('medeniyet', '')}\n\n"
            f"{result.get('cografi', '')}\n\n"
            "## Tarihsel bağlam\n\n"
            f"{result.get('tarihsel_baglam', '')}"
        )

        archaeology = (
            "## Kullanım amacı\n\n"
            f"{result.get('amac', '')}\n\n"
            "## Arkeolojik değerlendirme\n\n"
            f"{result.get('arkeoloji', '')}\n\n"
            "## Benzer eserlerle karşılaştırma\n\n"
            f"{result.get('karsilastirma', '')}\n\n"
            "## Korunma durumu\n\n"
            f"{result.get('korunma', '')}"
        )

        verification = (
            "## Belirsizlikler\n\n"
            f"{result.get('belirsizlikler', '')}\n\n"
            "## Nasıl doğrulanabilir?\n\n"
            f"{result.get('dogrulama', '')}"
        )

        sources = format_sources(result.get("kaynaklar", []))

        status = (
            "Analiz tamamlandı. Bu sonuç, görselden elde edilen bir ön "
            "değerlendirmedir; müze kaydı, uzman incelemesi veya arkeolojik "
            "belgeyle doğrulanmış bir kimlik tespiti olarak değerlendirilmemelidir."
        )

        return (
            identity,
            physical,
            history,
            archaeology,
            verification,
            sources,
            status
        )

    except requests.exceptions.Timeout:
        message = (
            "## Zaman aşımı\n\n"
            "API 90 saniye içinde yanıt vermedi. Biraz sonra tekrar dene."
        )
        return (message,) * 7

    except requests.exceptions.RequestException as error:
        message = f"## Bağlantı hatası\n\n`{str(error)}`"
        return (message,) * 7

    except (ValueError, json.JSONDecodeError) as error:
        message = (
            "## Yanıt okunamadı\n\n"
            "Model beklenen biçimde yanıt vermedi. Yeniden dene.\n\n"
            f"**Ayrıntı:** {str(error)}"
        )
        return (message,) * 7

    except Exception as error:
        message = (
            "## Beklenmeyen hata\n\n"
            "Uygulama beklenmeyen bir hata aldı.\n\n"
            f"**Hata türü:** `{type(error).__name__}`\n\n"
            f"**Ayrıntı:** {str(error)[:800]}"
        )
        return (message,) * 7


# =========================
# ARAYÜZ
# =========================

with gr.Blocks(
    title="Tarihinİzi | Tarihî Eser Analizi",
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="gray",
        neutral_hue="slate"
    ),
    css=CSS
) as app:

    gr.HTML(HEADER)

    gr.Markdown(
        "Bir tarihî eser fotoğrafı yükle. Sistem; olası kimliğini, "
        "dönemini, sanat özelliklerini ve doğrulama yollarını incelemeye çalışsın."
    )

    with gr.Row():
        with gr.Column(scale=1):
            image_input = gr.Image(
                label="Tarihî eser görseli",
                type="pil",
                height=350
            )

            extra_input = gr.Textbox(
                label="Ek bilgi (isteğe bağlı)",
                placeholder="Örneğin: Müze adı, bulunduğu şehir, üzerindeki yazı...",
                lines=3
            )

            analyze_button = gr.Button(
                "🇹🇷 ESERİ ANALİZ ET",
                variant="primary",
                size="lg"
            )

            clear_button = gr.Button("Temizle", variant="secondary")

        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab("Genel Bakış"):
                    out_identity = gr.Markdown()

                with gr.Tab("Fiziksel ve Sanatsal Özellikler"):
                    out_physical = gr.Markdown()

                with gr.Tab("Tarih ve Medeniyet"):
                    out_history = gr.Markdown()

                with gr.Tab("Arkeoloji"):
                    out_archaeology = gr.Markdown()

                with gr.Tab("Kanıtlar ve Belirsizlikler"):
                    out_verification = gr.Markdown()

                with gr.Tab("Kaynak Önerileri"):
                    out_sources = gr.Markdown()

    out_status = gr.Markdown(
        "🇹🇷 Hazır. Analiz başlatmak için bir görsel yükle."
    )

    outputs = [
        out_identity,
        out_physical,
        out_history,
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
        fn=lambda: (None, "", "", "", "", "", "", "", ""),
        inputs=[],
        outputs=[
            image_input,
            extra_input,
            out_identity,
            out_physical,
            out_history,
            out_archaeology,
            out_verification,
            out_sources,
            out_status
        ]
    )

# Render'ın verdiği PORT değerini kullan.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.queue().launch(
        server_name="0.0.0.0",
        server_port=port
    )
