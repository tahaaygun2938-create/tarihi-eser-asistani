
%pip -q install -U gradio requests pillow

import gradio as gr
import requests
import json
import base64
import time
import io
import re
from PIL import Image

# Ortamda tanımlı bir global anahtar var mı kontrol et
global_anahtar = globals().get("anahtar", "")


def gemini_istegi(govde, api_key):
    """Geçici sunucu hatalarında Gemini isteğini tekrar dener."""
    aktif_model = "models/gemini-3.8-flash"
    adres = f"https://generativelanguage.googleapis.com/v1beta/{aktif_model}:generateContent"

    for deneme in range(4):
        try:
            cevap = requests.post(
                adres,
                headers={"x-goog-api-key": api_key},
                json=govde,
                timeout=90
            )
        except requests.RequestException:
            if deneme < 3:
                time.sleep(2 ** (deneme + 1))
                continue
            raise RuntimeError(
                "Gemini sunucusuna bağlanılamadı. Biraz sonra tekrar dene."
            )

        if cevap.status_code == 200:
            return cevap.json()

        if cevap.status_code in [429, 500, 502, 503, 504]:
            if deneme < 3:
                time.sleep(2 ** (deneme + 1))
                continue

        raise RuntimeError(
            f"Gemini HTTP {cevap.status_code}: {cevap.text[:700]}"
        )

    raise RuntimeError("Gemini isteği tamamlanamadı.")


def eser_ara(fotograf_yolu, kullanici_anahtari):
    api_key = (
        kullanici_anahtari.strip()
        if kullanici_anahtari
        else global_anahtar
    )

    if not api_key:
        return (
            "HATA: Gemini API anahtarı bulunamadı! "
            "Lütfen aşağıdaki alana API anahtarınızı girin.",
            "Anahtar Eksik",
            "Anahtar Eksik",
            "Anahtar Eksik"
        )

    if not fotograf_yolu:
        return (
            "Lütfen bir fotoğraf yükleyin.",
            "Henüz bilgi yok.",
            "Henüz bilgi yok.",
            "Henüz kaynak yok."
        )

    try:
        # Fotoğrafı JPEG formatına dönüştür ve sıkıştır
        with Image.open(fotograf_yolu) as im:
            im = im.convert("RGB")
            im.thumbnail((1200, 1200))

            tampon = io.BytesIO()
            im.save(tampon, format="JPEG", quality=85)
            foto_bytes = tampon.getvalue()

        foto_base64 = base64.b64encode(foto_bytes).decode("utf-8")

        prompt = """
Sen tarihî eserler üzerine çalışan dikkatli bir arkeoloji ve sanat tarihi uzmanısın.
Ekli fotoğrafı görsel olarak incele.

Yalnızca geçerli bir JSON nesnesi döndür. Markdown kod çiti ekleme.

Şu anahtarları içeren bir yapı oluştur:

{
  "eser_adi": "Eserin veya yapının olası adı",
  "guven": "Düşük, Orta veya Yüksek; gerekçesiyle birlikte",
  "genel_bakis": "Eserin genel görünümü, mimari formu ve tanıtımı",
  "tarihce": "Tahmini dönem, inşa tarihi, uygarlık ve tarihsel bağlam",
  "arkeolojik_bulgular": "Gözlenen yapısal özellikler, malzeme, figürler ve süslemeler",
  "tarihsel_onem": "Kültürel, sanatsal ve tarihsel önem",
  "belirsizlikler": "Alternatif olasılıklar ve kesin saptanamayan ayrıntılar"
}

KURALLAR:
- Türkçe yaz ve her bölümü ayrıntılı açıkla.
- Tahminleri kesin gerçekler gibi sunma.
- Fotoğrafta görünmeyen arkeolojik unsurları veya konumları uydurma.
- Eserin konumu kesin bilinmiyorsa bunu açıkça belirt.
- Tarihsel bilgileri görselden kesin biçimde çıkaramayacağını belirt.
"""

        govde = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": foto_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.35,
                "responseMimeType": "application/json"
            }
        }

        sonuc = gemini_istegi(govde, api_key)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            return (
                "Yapay zekâ yanıt üretemedi.",
                "",
                "",
                ""
            )

        metin = adaylar[0].get(
            "content", {}
        ).get("parts", [{}])[0].get("text", "").strip()

        metin_temiz = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            metin,
            flags=re.IGNORECASE
        ).strip()

        try:
            bilgi = json.loads(metin_temiz)
        except json.JSONDecodeError:
            return (
                f"### Araştırma Dosyası\n\n{metin_temiz}",
                "Ayrı tarihçe oluşturulamadı.",
                "Ayrı bulgu oluşturulamadı.",
                "Kaynak saptanamadı."
            )

        eser_adi = str(
            bilgi.get("eser_adi", "Olası Tarihî Eser")
        )
        guven = str(
            bilgi.get("guven", "Güven düzeyi belirlenemedi.")
        )

        genel = (
            f"# 🏛️ {eser_adi}\n\n"
            f"**Tahmini Güven Düzeyi:** {guven}\n\n"
            f"### 📝 Genel Tanıtım\n"
            f"{bilgi.get('genel_bakis', 'Bilgi bulunamadı.')}\n\n"
            f"### 🌟 Tarihsel Önemi\n"
            f"{bilgi.get('tarihsel_onem', 'Bilgi bulunamadı.')}"
        )

        tarihce = (
            "## 📜 Dönem, Uygarlık ve Tarihçe\n\n"
            f"{bilgi.get('tarihce', 'Yeterli bilgi bulunamadı.')}"
        )

        bulgular = (
            "## 🔎 Arkeolojik Bulgular ve Detaylar\n\n"
            f"{bilgi.get('arkeolojik_bulgular', 'Yeterli bilgi bulunamadı.')}\n\n"
            "### ⚠️ Belirsizlikler ve Tartışmalar\n"
            f"{bilgi.get('belirsizlikler', 'Bu tanımlama kesin değildir.')}"
        )

        kaynaklar = (
            "## 📚 Önerilen Tarihsel Kaynaklar\n\n"
            "- **UNESCO Dünya Mirası Arşivleri**\n"
            "- **Kültür Portalı ve Bakanlık Envanterleri**\n"
            "- **Akademik Arkeoloji Yayınları ve Tez Çalışmaları**\n\n"
            "*Not: Bu analiz yapay zekâ tarafından oluşturulan "
            "bir ön araştırmadır. Önerilen kurumlar doğrudan "
            "doğrulanmış kaynaklar anlamına gelmez.*"
        )

        return genel, tarihce, bulgular, kaynaklar

    except Exception as hata:
        mesaj = f"Hata: {type(hata).__name__} - {str(hata)[:500]}"
        return mesaj, "", "", ""


# Tasarım ve stil ayarları
css = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}

/* Ana başlık */
#hero {
    padding: 42px 22px;
    border-radius: 22px;
    text-align: center;
    background: linear-gradient(135deg, #202321, #17151b, #292116);
    border: 1px solid #806b40;
    position: relative;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(30px, 5vw, 48px);
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 22px auto;
    background: linear-gradient(90deg, transparent, #e5c47a, transparent);
}

/* Altın renkli buton */
button.primary {
    background: linear-gradient(90deg, #a77b32, #e2c477) !important;
    color: #17130b !important;
    border: none !important;
    font-weight: bold !important;
}

/* Paneller */
.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}

/* Türk bayrağı: sağ üst köşe */
#turk-bayragi {
    position: fixed !important;
    top: 18px !important;
    right: 22px !important;
    width: 68px !important;
    height: auto !important;
    z-index: 99999 !important;
    border: 1px solid #e5c47a;
    border-radius: 4px;
    box-shadow: 0 3px 14px rgba(0, 0, 0, 0.45);
    pointer-events: none;
}

@media (max-width: 600px) {
    #turk-bayragi {
        width: 45px !important;
        top: 10px !important;
        right: 10px !important;
    }

    #hero {
        padding: 55px 15px 30px;
    }
}
"""


with gr.Blocks(
    title="Tarihî Eser Asistanı",
    css=css
) as uygulama:

    # Türk bayrağı
    gr.HTML("""
    <img
        id="turk-bayragi"
        src="https://upload.wikimedia.org/wikipedia/commons/b/b4/Flag_of_Turkey.svg"
        alt="Türk Bayrağı"
    >
    """)

    # Karşılama alanı
    gr.HTML("""
    <div id="hero">
        <div style="font-size:42px">🏛️</div>
        <h1>TARİHİN İZİNİ SÜR</h1>
        <div class="gold-line"></div>
        <p>Geçmişin izlerini keşfet. Eserleri tanı, tarihlerini araştır.</p>
        <p style="font-size:12px;letter-spacing:3px">
            TARİH • ARKEOLOJİ • KEŞİF
        </p>
    </div>
    """)

    gr.Markdown("### Yeni bir keşfe hazır mısın?")

    with gr.Group(elem_classes=["panel"]):

        api_anahtar_girdisi = gr.Textbox(
            label="Gemini API Anahtarı",
            placeholder="AIzaSy...",
            info="Ortamda anahtar tanımlamadıysan buraya gir.",
            type="password",
            value=""
        )

        fotograf_girdisi = gr.Image(
            label="Eser fotoğrafı yükleyin",
            type="filepath",
            height=320
        )

        arastir_butonu = gr.Button(
            "✦ KEŞFİ BAŞLAT",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():

        with gr.Tab("📜 Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Fotoğraf yüklendikten sonra analiz ve özet burada görünecek."
            )

        with gr.Tab("🏺 Tarihçe"):
            tarihce_cikti = gr.Markdown(
                "Dönem, uygarlık ve tarihsel bağlam bilgileri burada listelenecek."
            )

        with gr.Tab("🔎 Arkeolojik Bulgular"):
            bulgu_cikti = gr.Markdown(
                "Mimari bulgular, taş işçiliği ve olası belirsizlikler burada listelenecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Önerilen tarihsel araştırma kaynakları burada görüntülenecek."
            )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[
            fotograf_girdisi,
            api_anahtar_girdisi
        ],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            bulgu_cikti,
            kaynak_cikti
        ],
        show_progress="full"
    )


uygulama.launch(share=True)
