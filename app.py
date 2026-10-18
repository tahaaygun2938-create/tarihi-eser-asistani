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

        # Geçici sunucu yoğunluğu veya istek sınırı
        if cevap.status_code in [429, 500, 502, 503, 504]:
            if deneme < 3:
                time.sleep(2 ** (deneme + 1))
                continue

        raise RuntimeError(
            f"Gemini HTTP {cevap.status_code}: {cevap.text[:700]}"
        )

    raise RuntimeError("Gemini isteği tamamlanamadı.")

def eser_ara(fotograf_yolu, kullanici_anahtari):
    # Hangi anahtarın kullanılacağını belirle
    api_key = kullanici_anahtari.strip() if kullanici_anahtari else global_anahtar

    if not api_key:
        return (
            "HATA: Gemini API anahtarı bulunamadı! Lütfen aşağıdaki alana API anahtarınızı girin veya yukarıdaki 'anahtar' tanımlama hücresini çalıştırın.",
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
        # 1. Fotoğrafı güvenli biçimde JPEG'e dönüştür ve sıkıştır
        with Image.open(fotograf_yolu) as im:
            im = im.convert("RGB")
            im.thumbnail((1200, 1200))
            tampon = io.BytesIO()
            im.save(tampon, format="JPEG", quality=85)
            foto_bytes = tampon.getvalue()

        foto_base64 = base64.b64encode(foto_bytes).decode("utf-8")

        # 2. Gemini'den JSON çıktısı al
        prompt = """
Sen tarihî eserler üzerine çalışan son derece dikkatli bir arkeoloji ve sanat tarihi uzmanısın.
Ekli fotoğrafı görsel olarak en ince ayrıntısına kadar incele.

Yalnızca geçerli bir JSON nesnesi döndür. Markdown kod çiti (```json ... ```) ekleme.
Şu anahtarları içeren bir yapı oluştur:

{
  "eser_adi": "Eserin/Yapının olası adı",
  "guven": "Tahmini güven düzeyi (Düşük, Orta veya Yüksek; gerekçesiyle birlikte)",
  "genel_bakis": "Eserin genel görünümü, mimari formu ve tanıtıcı açıklaması",
  "tarihce": "Tahmini dönem, inşa tarihi, ilişkili olduğu uygarlık/hükümranlık ve tarihsel bağlamı",
  "arkeolojik_bulgular": "Fotoğrafta gözlenen yapısal özellikler, malzeme, figürler, süslemeler ve tarz detayları",
  "tarihsel_onem": "Eserin kültürel, sanatsal ve tarihsel önemi, varsa günümüzdeki koruma statüsü",
  "belirsizlikler": "Alternatif olasılıklar, kesin saptanamayan detaylar ve bilimsel tartışmalar"
}

KURALLAR:
- Türkçe yaz ve her bölümü olabildiğince detaylı/kapsamlı kolajlar halinde açıkla.
- Tahminleri kesin birer gerçekmiş gibi sunma; güven derecesini açıkça yansıt.
- Fotoğrafta görünmeyen arkeolojik unsurları veya konumları uydurma.
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
            return ("Yapay zekâ yanıt üretemedi.", "", "", "")

        metin = adaylar[0].get("content", {}).get("parts", [])[0].get("text", "").strip()

        # JSON temizleme
        metin_temiz = re.sub(r"^```(?:json)?\s*|\s*```$", "", metin, flags=re.IGNORECASE).strip()

        try:
            bilgi = json.loads(metin_temiz)
        except json.JSONDecodeError:
            return (f"### Araştırma Dosyası\n\n{metin_temiz}", "Ayrı tarihçe oluşturulamadı.", "Ayrı bulgu oluşturulamadı.", "Kaynak saptanamadı.")

        eser_adi = str(bilgi.get("eser_adi", "Olası Tarihî Eser"))
        guven = str(bilgi.get("guven", "Güven düzeyi belirlenemedi."))

        genel = (
            f"# 🏛️ {eser_adi}\n\n"
            f"**Tahmini Güven Düzeyi:** {guven}\n\n"
            f"### 📝 Genel Tanıtım\n"
            f"{bilgi.get('genel_bakis', 'Bilgi bulunamadı.')}\n\n"
            f"### 🌟 Tarihsel Önemi\n"
            f"{bilgi.get('tarihsel_onem', 'Bilgi bulunamadı.')}"
        )

        tarihce = (
            f"## 📜 Dönem, Uygarlık ve Tarihçe\n\n"
            f"{bilgi.get('tarihce', 'Yeterli bilgi bulunamadı.')}"
        )

        bulgular = (
            f"## 🔎 Arkeolojik Bulgular ve Detaylar\n\n"
            f"{bilgi.get('arkeolojik_bulgular', 'Yeterli bilgi bulunamadı.')}\n\n"
            f"### ⚠️ Belirsizlikler ve Tartışmalar\n"
            f"{bilgi.get('belirsizlikler', 'Bu tanımlama kesin değildir.')}"
        )

        kaynaklar = (
            "## 📚 Önerilen Tarihsel Kaynaklar\n\n"
            "- **UNESCO Dünya Mirası Arşivleri**\n"
            "- **Kültür Portalı ve Bakanlık Envanterleri**\n"
            "- **Akademik Arkeoloji Yayınları, Tez Çalışmaları ve Monografiler**\n\n"
            "*Not: Bu analiz yapay zekâ tarafından sunulan bir ön araştırmadır. Kesin teşhis ancak yerinde arkeolojik uzman incelemeleriyle mümkündür.*"
        )

        return genel, tarihce, bulgular, kaynaklar

    except Exception as hata:
        mesaj = f"Hata: {type(hata).__name__} - {str(hata)[:500]}"
        return (mesaj, "", "", "")

# Tasarım ve Stil Ayarları
css = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}
#hero {
    padding: 42px 22px;
    border-radius: 22px;
    text-align: center;
    background: linear-gradient(135deg, #202321, #17151b, #292116);
    border: 1px solid #806b40;
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
button.primary {
    background: linear-gradient(90deg, #a77b32, #e2c477) !important;
    color: #17130b !important;
    border: none !important;
    font-weight: bold !important;
}
.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}
"""

with gr.Blocks(title="Tarihî Eser Asistanı", css=css) as uygulama:
    gr.HTML("""
    <div id="hero">
      <div style="font-size:42px">🏛️</div>
      <h1>TARİHİN İZİNİ SÜR</h1>
      <div class="gold-line"></div>
      <p>Geçmişin izlerini keşfet. Eserleri tanı, tarihlerini araştır.</p>
      <p style="font-size:12px;letter-spacing:3px">TARİH • ARKEOLOJİ • KEŞİF</p>
    </div>
    """)

    gr.Markdown("### Yeni bir keşfe hazır mısın?")

    with gr.Group(elem_classes=["panel"]):
        api_anahtar_girdisi = gr.Textbox(
            label="Gemini API Anahtarı (Opsiyonel - Eğer yukarıda tanımlanmadıysa buraya girin)",
            placeholder="AIzaSy...",
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
                "Önerilen tarihsel araştırma referansları burada görüntülenecek."
            )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[fotograf_girdisi, api_anahtar_girdisi],
        outputs=[genel_cikti, tarihce_cikti, bulgu_cikti, kaynak_cikti],
        show_progress="full"
    )

uygulama.launch(share=True)
