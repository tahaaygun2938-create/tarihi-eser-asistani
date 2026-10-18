
import os
import io
import re
import time
import html
import base64
import requests
import gradio as gr
from PIL import Image

# ===================== AYARLAR =====================

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODEL
    + ":generateContent"
)

IMAGE_SIZE = (1400, 1400)
IMAGE_QUALITY = 85

SECTIONS = [
    ("GENEL_BAKIS", "🏛️ Genel Bakış"),
    ("GORSEL_INCELEME", "🔎 Görsel İnceleme"),
    ("TARIHCE", "📜 Ayrıntılı Tarihçe"),
    ("KRONOLOJI", "🗓️ Kronoloji"),
    ("MIMARI_SANAT", "🎨 Mimari ve Sanat"),
    ("ARKEOLOJI", "⛏️ Arkeoloji"),
    ("TARIHSEL_BAGLAM", "🌍 Tarihsel Bağlam"),
    ("TURK_TARIHI", "🇹🇷 Türk Tarihi"),
    ("KARSILASTIRMA", "⚖️ Karşılaştırma"),
    ("KORUMA", "🛡️ Koruma"),
    ("ONEM", "⭐ Tarihsel Önem"),
    ("BELIRSIZLIKLAR", "❔ Belirsizlikler"),
    ("KAYNAKLAR", "📚 Kaynaklar"),
    ("SONUC", "📝 Genel Sonuç"),
]

PROMPT = r"""
Sen tarih, arkeoloji, sanat tarihi ve kültürel miras alanlarında
çalışan dikkatli bir araştırma asistanısın.

Yüklenen fotoğraftaki tarihî eseri veya yapıyı tanımlamaya çalış.
Türkçe, kapsamlı ve kaynakları denetlenebilir bir araştırma raporu hazırla.

KURALLAR:
- Görselde doğrudan görülenlerle tarihsel yorumları ayır.
- Kimlik kesin değilse olası seçenekleri ve gerekçelerini açıkla.
- Yalnızca fotoğrafa bakarak kesin tarih veya köken iddiasında bulunma.
- Kaynak, kitap, kazı raporu, envanter numarası veya alıntı uydurma.
- Türk tarihiyle bağlantı kanıtlanamıyorsa bunu açıkça belirt.
- Genel dönem bilgisini bu esere ilişkin doğrudan kanıt gibi sunma.
- Google Arama aracı kullanılabiliyorsa müze, üniversite, resmî
  kurum ve akademik kaynakları araştır.
- Bir bağlantının bulunması, iddiayı doğruladığı anlamına gelmez.
- Güncel bilgiler doğrulanamıyorsa bunu açıkça söyle.
- Aynı bilgiyi tekrar ederek raporu uzatma.
- Yanıtın tamamı Türkçe olsun.

Aşağıdaki etiketleri aynen kullan:

[[GENEL_BAKIS]]
Muhtemel eser adı, alternatif adları, türü, olası uygarlığı,
tahmini dönemi, tarihlendirme gerekçesi ve teşhis güven düzeyi.

[[GORSEL_INCELEME]]
Görülen biçimler, malzeme izlenimi, motifler, yazılar, yüzey,
aşınma ve fotoğrafın sınırları. Gözlemle yorumu ayır.

[[TARIHCE]]
Eserin ortaya çıktığı tarihsel ortam, yapılış amacı, kullanımı,
tarih boyunca değişimleri, terk edilmesi, yeniden keşfi,
kazılar, restorasyonlar ve günümüze ulaşması. Bilinmeyenleri uydurma.

[[KRONOLOJI]]
Tarih, olay ve açıklama sütunlarıyla kronoloji tablosu oluştur.
Yaklaşık ve bilinmeyen tarihleri açıkça belirt.

[[MIMARI_SANAT]]
Mimari biçim, oran, malzeme, yapım tekniği, süsleme,
motifler, sanat üslubu ve benzer eserlerle ilişkiler.

[[ARKEOLOJI]]
Biliniyorsa buluntu yeri, arkeolojik bağlam, kazı geçmişi,
tarihlendirme yöntemleri, katalog bilgileri ve bilimsel tartışmalar.

[[TARIHSEL_BAGLAM]]
Dönemin yönetimi, toplum, ekonomi, ticaret, inanç, askerî yapı,
dil ve kültürü. Genel bilgileri doğrudan kanıt olarak sunma.

[[TURK_TARIHI]]
Türk devletleri, toplulukları, Selçuklu, Osmanlı veya Anadolu
beylikleriyle bağlantıları kaynaklarla değerlendir.
Doğrudan bağlantı kanıtlanamıyorsa bunu söyle.

[[KARSILASTIRMA]]
Güvenilir kaynaklarla belirlenebiliyorsa en fazla üç benzer eseri
tarih, konum, malzeme, üslup ve farklılıklar bakımından karşılaştır.

[[KORUMA]]
Bilinen konum, koruma durumu, restorasyon, riskler ve resmî
miras statüsü. Güncel bilgi doğrulanamıyorsa belirt.

[[ONEM]]
Eserin tarih, arkeoloji, sanat ve mimarlık tarihi açısından önemi.

[[BELIRSIZLIKLAR]]
Kimlik ve tarihlendirme tartışmaları, kaynak uyuşmazlıkları,
fotoğraftan belirlenemeyen özellikler ve gereken ek kanıtlar.

[[KAYNAKLAR]]
Gerçekten araştırma sırasında bulunan kaynakların başlığı,
kurumu/yazarı, bağlantısı ve desteklediği iddia. Kaynak bulunamazsa
bunu açıkça yaz. Genel internet sitelerini doğrulanmış eser
kaynaklarıymış gibi gösterme.

[[SONUC]]
En güçlü teşhis, güven düzeyi, temel bulgular, belirsizlikler
ve daha iyi teşhis için gereken ek bilgiler.
"""


# ===================== FOTOĞRAF =====================

def prepare_image(path):
    with Image.open(path) as original:
        image = original.convert("RGB")
        image.thumbnail(IMAGE_SIZE)

        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=IMAGE_QUALITY,
            optimize=True
        )

        return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ===================== GEMINI API =====================

def ask_gemini(image_data):
    if not API_KEY:
        raise RuntimeError(
            "API anahtarı eksik. Render > Environment bölümüne "
            "GEMINI_API_KEY değişkenini ekle."
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
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 12000
        },
        "tools": [
            {"google_search": {}}
        ]
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
            detail = error_data.get("error", {}).get(
                "message", response.text
            )
        except ValueError:
            detail = response.text

        if response.status_code == 429:
            raise RuntimeError(
                "Gemini API kotası veya istek sınırı aşıldı (429). "
                "Google AI Studio'dan model kotanı kontrol et. "
                + str(detail)[:600]
            )

        raise RuntimeError(
            f"Gemini API HTTP {response.status_code}: "
            + str(detail)[:800]
        )

    data = response.json()
    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Model yanıt üretmedi. "
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
        raise RuntimeError("Model boş yanıt verdi.")

    # Yalnızca API yanıtında gerçekten dönen arama bağlantıları.
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


# ===================== RAPOR BÖLÜMLERİ =====================

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


def make_source_text(sources):
    if not sources:
        return (
            "API yanıtında doğrulanabilir arama bağlantısı alınamadı. "
            "Bu nedenle esere ait doğrulanmış kaynak listesi "
            "sunulamıyor. Bilgileri ayrıca kontrol et."
        )

    lines = [
        "Aşağıdaki bağlantılar API yanıtındaki arama "
        "metaverisinden alınmıştır. İlgili iddiaları destekleyip "
        "desteklemediklerini kaynak sayfalarında kontrol et."
    ]

    for number, (title, url) in enumerate(sources, start=1):
        safe_title = html.escape(title)
        safe_url = html.escape(url, quote=True)
        lines.append(f"{number}. [{safe_title}]({safe_url})")

    return "\n\n".join(lines)


# ===================== ANA İŞLEM =====================

def analyze_artifact(image_path):
    empty_results = ("",) * len(SECTIONS)

    if not image_path:
        return (
            "Önce bir tarihî eser fotoğrafı yükle.",
        ) + empty_results[1:]

    started = time.perf_counter()

    try:
        image_data = prepare_image(image_path)
        report, sources = ask_gemini(image_data)
        sections = split_report(report)

        # Bölüm etiketleri beklenmedik biçimde eksikse raporu koru.
        if len(sections) < 4:
            sections["GENEL_BAKIS"] = report

        source_text = make_source_text(sources)

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
                "Genel bakış bölümü oluşturulamadı."
            )
            + f"\n\n---\n\n*İşlem süresi: {elapsed:.1f} saniye · "
            + f"Arama bağlantısı: {len(sources)}*"
        )

        results = []

        for key, _label in SECTIONS:
            results.append(
                sections.get(
                    key,
                    "Bu bölüm ayrı bir başlık altında oluşturulamadı. "
                    "Genel Bakış bölümündeki raporu incele."
                )
            )

        return tuple(results)

    except Exception as error:
        message = (
            "## Araştırma sırasında hata oluştu\n\n"
            f"**Hata türü:** `{type(error).__name__}`\n\n"
            f"**Ayrıntı:** {str(error)[:1000]}\n\n"
            "Gerekirse Render > Logs bölümündeki hata mesajını "
            "kontrol et."
        )

        return (message,) + empty_results[1:]


# ===================== TASARIM =====================

CSS = """
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
    background: #11100e !important;
    color: #eee7d8 !important;
}

body {
    background: #11100e !important;
}

#hero {
    text-align: center;
    padding: 30px 18px 20px;
    border-bottom: 1px solid #66502b;
    margin-bottom: 20px;
}

#hero h1 {
    color: #e3c98e;
    font-family: Georgia, serif;
    letter-spacing: 2px;
    font-size: clamp(26px, 4vw, 42px);
}

#hero p {
    color: #c5bba7;
}

#flag {
    position: absolute;
    top: 14px;
    right: 16px;
    z-index: 10;
    text-align: center;
}

#flag img {
    display: block;
    width: 54px;
    height: auto;
    border: 1px solid #d9b878;
    border-radius: 4px;
}

#flag small {
    display: block;
    margin-top: 5px;
    color: #d9b878;
    font-size: 9px;
}

.panel {
    border: 1px solid #66502b !important;
    border-radius: 12px !important;
}

button.primary {
    background: #a77c35 !important;
    color: white !important;
}
"""


# ===================== GRADIO ARAYÜZÜ =====================

with gr.Blocks(
    title="Tarihin İzini Sür | Kültür ve Miras",
    css=CSS,
    theme=gr.themes.Soft(
        primary_hue="amber",
        secondary_hue="stone",
        neutral_hue="slate"
    )
) as app:

    gr.HTML("""
    <div id="flag">
        <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
            alt="Türk bayrağı"
        >
        <small>by Taha Anıl Aygün</small>
    </div>

    <div id="hero">
        <h1>TARİHİN İZİNİ SÜR</h1>
        <p>Bir fotoğrafın ardındaki tarihi keşfet.</p>
        <p>TARİH • ARKEOLOJİ • TÜRK KÜLTÜRÜ • MİRAS</p>
    </div>
    """)

    gr.Markdown(
        "Bir tarihî eser fotoğrafı yükle. Uygulama eseri "
        "tanımlamaya ve ayrıntılı bir araştırma raporu "
        "hazırlamaya çalışsın."
    )

    with gr.Group(elem_classes=["panel"]):
        image_input = gr.Image(
            type="filepath",
            label="Tarihî eser fotoğrafı",
            sources=["upload"]
        )

        submit_button = gr.Button(
            "Eseri Araştır",
            variant="primary",
            size="lg"
        )

    with gr.Tabs():
        outputs = []

        for _key, label in SECTIONS:
            with gr.Tab(label):
                outputs.append(gr.Markdown())

    gr.Markdown(
        "> **Bilgilendirme:** Yapay zekâ hata yapabilir. "
        "Eserin kimliğini, tarihini ve kaynakları ayrıca doğrula."
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.launch(
        server_name="0.0.0.0",
        server_port=port
    )
