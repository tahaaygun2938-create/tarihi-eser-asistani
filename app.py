
import os
import io
import re
import time
import base64
import html
import requests
import gradio as gr
from PIL import Image

# ==================================================
# TARİHİNİZİ — UYGULAMA AYARLARI
# ==================================================

APP_NAME = "Tarihinİzi"
MODEL = "gemini-3.5-flash-lite"

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)

SECTIONS = [
    ("GENEL_BAKIS", "🏛️ Genel Bakış"),
    ("GORSEL_INCELEME", "🔎 Görsel İnceleme"),
    ("TARIHCE", "📜 Tarihçe"),
    ("KRONOLOJI", "🗓️ Kronoloji"),
    ("MIMARI_SANAT", "🎨 Mimari ve Sanat"),
    ("ARKEOLOJI", "⛏️ Arkeoloji"),
    ("TARIHSEL_BAGLAM", "🌍 Tarihsel Bağlam"),
    ("TURK_TARIHI", "🇹🇷 Türk Tarihi"),
    ("KARSILASTIRMA", "⚖️ Karşılaştırma"),
    ("KORUMA", "🛡️ Koruma"),
    ("ONEM", "⭐ Tarihsel Önemi"),
    ("BELIRSIZLIKLAR", "❔ Belirsizlikler"),
    ("KAYNAKLAR", "📚 Kaynaklar"),
    ("SONUC", "📝 Sonuç"),
]

PROMPT = """
Sen Tarihinİzi adlı tarih araştırma uygulamasının uzman
araştırma asistanısın. Tarih, arkeoloji, sanat tarihi,
mimarlık ve kültürel miras alanlarında çalışıyorsun.

Kullanıcının gönderdiği fotoğrafı incele ve Türkçe bir
araştırma raporu hazırla.

TEMEL KURALLAR:
- Önce eserin ne olabileceğini belirle.
- Görselde gerçekten görülen ayrıntılarla yorumları ayır.
- Emin değilsen tek bir kimliği kesinmiş gibi sunma.
- Eserin adını, konumunu, tarihini veya kökenini uydurma.
- Türk tarihi bağlantılarını kanıt yoksa kesinleştirme.
- Genel tarih bilgisini eser hakkında doğrudan kanıt gibi sunma.
- Mümkün olduğunda Google Arama ile güvenilir kaynakları araştır.
- Öncelikle müzeleri, üniversiteleri, resmî kurumları,
  akademik yayınları ve arkeolojik envanterleri kullan.
- Kaynak bağlantısı, kitap adı, yazar, alıntı veya envanter
  numarası uydurma.
- Kaynakların hangi iddiaları desteklediğini belirt.
- Kaynaklar arasında uyuşmazlık varsa açıkla.
- Her bölüm bilgi açısından dolu ama anlaşılır olsun.
- Bilinmeyen bilgileri açıkça belirt.
- Yanıtın tamamını Türkçe yaz.

RAPORU AŞAĞIDAKİ ETİKETLERLE DÜZENLE.
Etiketleri değiştirme; her birini ayrı başlıkta kullan.

[[GENEL_BAKIS]]
Eserin muhtemel adı, türü, olası uygarlığı, tahmini tarihi,
bulunduğu yer biliniyorsa konumu ve teşhis güven düzeyi.
Teşhisin hangi görsel özelliklere dayandığını açıkla.

[[GORSEL_INCELEME]]
Fotoğraftaki biçim, malzeme izlenimi, motifler, yazılar,
süslemeler, aşınmalar ve belirgin ayrıntılar.
Fotoğrafın hangi özellikleri belirlemeye yetmediğini de yaz.

[[TARIHCE]]
Eserin yapılış amacı, tarihsel ortamı, kullanım geçmişi,
önemli tarihsel olaylarla ilişkisi, keşfi ve biliniyorsa
restorasyon geçmişi.

[[KRONOLOJI]]
Önemli tarihleri ve olayları sıralı biçimde tabloyla göster.
Tarihler tahminîyse veya kesin bilinmiyorsa belirt.

[[MIMARI_SANAT]]
Mimari özellikler, sanat üslubu, malzeme, teknik,
süsleme anlayışı ve benzer sanat gelenekleri.

[[ARKEOLOJI]]
Biliniyorsa buluntu yeri, kazı geçmişi, arkeolojik bağlam,
envanter bilgileri ve tarihlendirme yöntemleri.

[[TARIHSEL_BAGLAM]]
Eserin dönemindeki toplum, yönetim, ekonomi, ticaret,
inançlar ve kültürel ilişkiler. Genel bilgilerle eser hakkında
doğrudan doğrulanmış bilgileri birbirinden ayır.

[[TURK_TARIHI]]
Eserin Türk devletleri, Anadolu tarihi, Selçuklular,
Osmanlılar veya Türk topluluklarıyla ilişkisini araştır.
İlişki kanıtlanamıyorsa bunu açıkça belirt.

[[KARSILASTIRMA]]
Güvenilir kaynaklarla belirlenebiliyorsa benzer eserlerle
karşılaştırma yap. Tarih, konum, malzeme ve üslup
farklılıklarını açıkla.

[[KORUMA]]
Eserin bilinen güncel konumu, koruma durumu, restorasyonları,
karşılaştığı riskler ve resmî koruma statüsü.
Güncel bilgi doğrulanamıyorsa bunu belirt.

[[ONEM]]
Eserin tarih, arkeoloji, mimarlık, sanat ve kültürel miras
açısından neden önemli olabileceğini açıkla.

[[BELIRSIZLIKLAR]]
Kimlik, tarih, köken ve kullanım hakkındaki belirsizlikler.
Uzmanların farklı görüşleri varsa kaynaklarıyla açıkla.
Daha kesin teşhis için hangi ek bilgilerin gerektiğini belirt.

[[KAYNAKLAR]]
Gerçekten araştırma sırasında bulunan kaynakları başlık,
kurum veya yazar, bağlantı ve desteklediği iddiayla listele.
Kaynak bulunamadıysa bunu açıkça yaz.
Doğrulanmayan bağlantıları kaynak olarak sunma.

[[SONUC]]
En güçlü teşhis, güven düzeyi, temel bulgular ve belirsizlikler.
Eserin kesin olarak tanımlanıp tanımlanamadığını özetle.
"""


# ==================================================
# FOTOĞRAF HAZIRLAMA
# ==================================================

def prepare_image(image_path):
    with Image.open(image_path) as original:
        image = original.convert("RGB")
        image.thumbnail((1400, 1400))

        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=85,
            optimize=True
        )

        return base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")


# ==================================================
# GEMINI 3.5 FLASH-LITE
# ==================================================

def ask_gemini(image_data):
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadı. Render > Environment "
            "bölümünden API anahtarını eklemelisin."
        )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }
        ],
        "tools": [
            {"google_search": {}}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 12000
        }
    }

    response = requests.post(
        API_URL,
        params={"key": API_KEY},
        json=payload,
        timeout=180
    )

    if not response.ok:
        try:
            error_data = response.json()
            error_message = error_data.get(
                "error", {}
            ).get("message", response.text)
        except ValueError:
            error_message = response.text

        if response.status_code == 429:
            raise RuntimeError(
                "API kullanım kotası veya istek sınırı aşıldı. "
                "Google AI Studio'daki model kotanı kontrol et. "
                + str(error_message)[:600]
            )

        raise RuntimeError(
            f"Gemini API HTTP {response.status_code}: "
            + str(error_message)[:800]
        )

    data = response.json()
    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Gemini yanıt üretmedi. Ayrıntı: "
            + str(data.get("promptFeedback", {}))[:500]
        )

    candidate = candidates[0]
    parts = candidate.get("content", {}).get("parts", [])

    report = "\n".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not report:
        raise RuntimeError(
            "Gemini boş yanıt verdi. Render Logs bölümünü kontrol et."
        )

    # Yalnızca API yanıtında bulunan arama bağlantılarını al.
    sources = []
    seen_urls = set()

    metadata = candidate.get("groundingMetadata", {}) or {}

    for chunk in metadata.get("groundingChunks", []) or []:
        web_info = chunk.get("web", {}) or {}
        url = web_info.get("uri", "")
        title = web_info.get("title", "Kaynak")

        if (
            url.startswith(("https://", "http://"))
            and url not in seen_urls
        ):
            seen_urls.add(url)
            sources.append((title, url))

    return report, sources


# ==================================================
# RAPORU BÖLÜMLERE AYIRMA
# ==================================================

def split_report(report):
    pattern = r"\[\[([A-Z_]+)\]\]"
    matches = list(re.finditer(pattern, report))
    sections = {}

    for index, match in enumerate(matches):
        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(report)

        sections[match.group(1)] = report[start:end].strip()

    return sections


def format_sources(sources):
    if not sources:
        return (
            "Arama yanıtından kaynak bağlantısı alınamadı. "
            "Bu, esere ait doğrulanmış kaynak bulunmadığı "
            "anlamına gelmez. Bilgileri ayrıca kontrol et."
        )

    lines = [
        "Aşağıdaki bağlantılar arama yanıtından alınmıştır. "
        "İlgili iddiaları destekleyip desteklemediklerini "
        "kaynak sayfalarında ayrıca kontrol et."
    ]

    for number, (title, url) in enumerate(sources, start=1):
        safe_title = html.escape(title)
        safe_url = html.escape(url, quote=True)

        lines.append(
            f"{number}. [{safe_title}]({safe_url})"
        )

    return "\n\n".join(lines)


# ==================================================
# ANA ANALİZ FONKSİYONU
# ==================================================

def analyze_artifact(image_path):
    if not image_path:
        message = "Önce analiz etmek istediğin eser fotoğrafını yükle."
        return (message,) + ("",) * (len(SECTIONS) - 1)

    started = time.perf_counter()

    try:
        image_data = prepare_image(image_path)
        report, sources = ask_gemini(image_data)
        sections = split_report(report)

        # Model etiketleri üretmezse raporu kaybetme.
        if len(sections) < 4:
            sections["GENEL_BAKIS"] = report

        source_text = format_sources(sources)

        if sections.get("KAYNAKLAR"):
            sections["KAYNAKLAR"] += (
                "\n\n---\n\n" + source_text
            )
        else:
            sections["KAYNAKLAR"] = source_text

        elapsed = time.perf_counter() - started

        sections["GENEL_BAKIS"] = (
            sections.get(
                "GENEL_BAKIS",
                "Genel bakış oluşturulamadı."
            )
            + f"\n\n---\n\n"
            + f"*Model: `{MODEL}` · "
            + f"Süre: {elapsed:.1f} saniye · "
            + f"Arama bağlantısı: {len(sources)}*"
        )

        results = []

        for key, _label in SECTIONS:
            results.append(
                sections.get(
                    key,
                    "Bu bölüm ayrı oluşturulamadı. "
                    "Genel Bakış bölümündeki raporu incele."
                )
            )

        return tuple(results)

    except Exception as error:
        message = (
            "## Araştırma sırasında hata oluştu\n\n"
            f"**Hata türü:** `{type(error).__name__}`\n\n"
            f"**Ayrıntı:** {str(error)[:1000]}\n\n"
            "Render > Logs bölümünü de kontrol edebilirsin."
        )

        return (message,) + ("",) * (len(SECTIONS) - 1)


# ==================================================
# TÜRK TEMALI TASARIM
# ==================================================

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --red: #b51f2b;
    --red-dark: #68131c;
    --gold: #d7b779;
    --cream: #f3eee5;
}

.gradio-container {
    max-width: 1250px !important;
    margin: auto !important;
    color: var(--cream) !important;
    font-family: 'Inter', sans-serif !important;
    background:
        radial-gradient(ellipse at 50% 0%, #49171e 0%, transparent 43%),
        linear-gradient(145deg, #171518, #100f12 55%, #241316) !important;
}

body {
    background: #100f12 !important;
}

#hero {
    position: relative;
    overflow: hidden;
    text-align: center;
    padding: 40px 20px 32px;
    margin: 12px 0 26px;
    border: 1px solid rgba(215,183,121,.32);
    border-radius: 20px;
    background:
        radial-gradient(ellipse at 50% 120%, rgba(181,31,43,.30), transparent 65%),
        linear-gradient(135deg, rgba(104,19,28,.32), rgba(20,18,21,.95) 70%);
    box-shadow: 0 12px 40px rgba(0,0,0,.30);
}

#hero:before {
    content: "";
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 2px;
    background: linear-gradient(
        90deg, transparent, #b51f2b, #d7b779, #b51f2b, transparent
    );
}

#hero h1 {
    font-family: 'Cinzel', Georgia, serif !important;
    font-size: clamp(34px, 5vw, 58px) !important;
    font-weight: 700 !important;
    letter-spacing: 2px;
    margin: 18px 0;
    background: linear-gradient(
        100deg, #f4e4c1, #d7b779 45%, #fff1d5 70%, #cba15d
    );
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 3px 15px rgba(181,31,43,.22));
}

#hero p {
    color: #c9c0b8 !important;
    letter-spacing: 1.3px;
}

#flag {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}

#flag img {
    width: 46px;
    height: 30px;
    object-fit: cover;
    border-radius: 4px;
    box-shadow: 0 0 18px rgba(181,31,43,.38);
}

#flag small {
    color: #d7b779;
    font-size: 10px;
    letter-spacing: 1.5px;
}

.panel, .gr-panel, .gr-box {
    border-color: rgba(215,183,121,.22) !important;
}

label, .prose, .markdown {
    color: #eee5db !important;
}

button.primary {
    background: linear-gradient(
        110deg, #74151f, #bd2734 55%, #8b1925
    ) !important;
    border: 1px solid rgba(235,192,137,.45) !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 700 !important;
    letter-spacing: .7px;
    box-shadow: 0 5px 18px rgba(181,31,43,.22);
    transition: .2s ease !important;
}

button.primary:hover {
    filter: brightness(1.15);
    box-shadow: 0 7px 24px rgba(181,31,43,.35);
}

button, input, textarea {
    border-radius: 9px !important;
}

.tab-nav button.selected {
    color: #f0ce91 !important;
    border-bottom: 2px solid #b51f2b !important;
}

footer {
    display: none !important;
}

@media (max-width: 600px) {
    #hero {
        padding: 28px 12px 22px;
    }

    #hero h1 {
        letter-spacing: 1px;
    }
}
"""


# ==================================================
# GRADIO ARAYÜZÜ
# ==================================================

with gr.Blocks(
    title="Tarihinİzi",
    css=CSS,
    theme=gr.themes.Soft(
        primary_hue="red",
        secondary_hue="amber",
        neutral_hue="slate"
    )
) as app:

    gr.HTML("""
    <div id="hero">
        <div id="flag">
            <img
                src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
                alt="Türk bayrağı"
            >
            <small>BY TAHA ANIL AYGÜN</small>
        </div>

        <h1>Tarihinİzi</h1>

        <p>GEÇMİŞİN İZİNDE, TARİHİN DERİNLİĞİNDE</p>
        <p>🇹🇷 TÜRK TARİHİ · ARKEOLOJİ · KÜLTÜREL MİRAS</p>
    </div>
    """)

    gr.Markdown(
        "Fotoğrafını yükle, eserin geçmişini keşfet. "
        "Tarihî eserleri 14 ayrı araştırma başlığında incele."
    )

    with gr.Group():
        image_input = gr.Image(
            type="filepath",
            label="🏛️ Tarihî eser fotoğrafı",
            sources=["upload"]
        )

        submit_button = gr.Button(
            "🇹🇷 ESERİ ARAŞTIR",
            variant="primary",
            size="lg"
        )

    with gr.Tabs():
        outputs = []

        for _key, label in SECTIONS:
            with gr.Tab(label):
                output = gr.Markdown()
                outputs.append(output)

    gr.Markdown(
        "> **Tarihinİzi:** Yapay zekâ destekli ön araştırma aracıdır. "
        "Eser kimliğini, tarihini ve kaynakları gerektiğinde "
        "akademik yayınlar ve resmî kurumlarla doğrula."
    )

    submit_button.click(
        fn=analyze_artifact,
        inputs=[image_input],
        outputs=outputs
    )

    image_input.change(
        fn=lambda: [""] * len(SECTIONS),
        inputs=[],
        outputs=outputs
    )


# ==================================================
# RENDER BAŞLATMA
# ==================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    app.launch(
        server_name="0.0.0.0",
        server_port=port
    )
