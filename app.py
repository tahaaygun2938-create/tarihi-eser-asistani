
import os
import json
import base64
import re
import requests
import gradio as gr

# API anahtarı kontrolü
if not globals().get("anahtar") or not anahtar.strip():
    raise ValueError(
        "API anahtarı bulunamadı. Önce anahtar değişkenini tanımla."
    )

# Model ayarı
MODEL = "gemini-3.5-flash-lite"


def eser_ara(fotograf_yolu):
    if not fotograf_yolu:
        mesaj = "Lütfen bir fotoğraf yükleyin."
        return mesaj, "Henüz bilgi yok.", "Henüz bilgi yok.", "Henüz kaynak yok."

    try:
        # Fotoğrafı JPEG'e dönüştür
        from PIL import Image
        from io import BytesIO

        with Image.open(fotograf_yolu) as resim:
            resim = resim.convert("RGB")
            cikti = BytesIO()
            resim.save(cikti, format="JPEG", quality=90)
            foto_base64 = base64.b64encode(
                cikti.getvalue()
            ).decode("utf-8")

        prompt = """
Sen dikkatli bir arkeoloji araştırma asistanısın.
Fotoğraftaki tarihî eser veya yapıyı Türkçe analiz et.

Yalnızca geçerli bir JSON nesnesi döndür.
Markdown kod bloğu kullanma.

Şu alanları doldur:
{
  "eser_adi": "Olası eser adı",
  "genel_bakis": "Eseri tanıtan açıklama",
  "tarihce": "Tahmini dönem, uygarlık ve kullanım amacı",
  "arkeolojik_bulgular": "Görülebilen mimari ve malzeme ayrıntıları",
  "tarihsel_onem": "Tarihsel ve kültürel önem",
  "belirsizlikler": "Bilinmeyenler ve alternatif olasılıklar"
}

Kurallar:
- Kanıt yoksa bunu açıkça belirt.
- Tarih, konum ve kaynak uydurma.
- Görsel benzerliğini kesin teşhis olarak sunma.
- Fotoğrafta görünmeyen ayrıntıları gerçekmiş gibi anlatma.
"""

        veri = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": foto_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            }
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{MODEL}:generateContent"
        )

        yanit = requests.post(
            url,
            headers={"x-goog-api-key": anahtar},
            json=veri,
            timeout=90
        )

        if yanit.status_code != 200:
            try:
                hata = yanit.json().get("error", {})
                hata_metni = hata.get(
                    "message", yanit.text[:700]
                )
                hata_durumu = hata.get("status", "")
            except ValueError:
                hata_metni = yanit.text[:700]
                hata_durumu = ""

            mesaj = (
                f"### Gemini API hatası: HTTP {yanit.status_code}\n\n"
                f"**Durum:** {hata_durumu or 'Belirtilmedi'}\n\n"
                f"**Açıklama:** {hata_metni}"
            )

            return mesaj, mesaj, mesaj, mesaj

        sonuc = yanit.json()
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            mesaj = (
                "Model kullanılabilir bir yanıt döndürmedi. "
                "İstek engellenmiş veya yanıt tamamlanmamış olabilir."
            )
            return mesaj, mesaj, mesaj, mesaj

        parcalar = adaylar[0].get(
            "content", {}
        ).get("parts", [])

        metin = "\n".join(
            parca["text"]
            for parca in parcalar
            if "text" in parca
        ).strip()

        if not metin:
            mesaj = "Modelden okunabilir metin alınamadı."
            return mesaj, mesaj, mesaj, mesaj

        # Olası Markdown kod bloğunu temizle
        metin = re.sub(r"^```(?:json)?\s*", "", metin)
        metin = re.sub(r"\s*```$", "", metin)

        try:
            bilgi = json.loads(metin)
        except json.JSONDecodeError:
            mesaj = (
                "Model yanıtı geçerli JSON biçiminde değil.\n\n"
                + metin
            )
            return mesaj, mesaj, mesaj, "Kaynaklar doğrulanamadı."

        eser_adi = bilgi.get("eser_adi", "Olası tarihî eser")
        genel_bakis = bilgi.get(
            "genel_bakis", "Yeterli bilgi bulunamadı."
        )
        tarihce_bilgi = bilgi.get(
            "tarihce", "Yeterli bilgi bulunamadı."
        )
        arkeolojik_bulgular = bilgi.get(
            "arkeolojik_bulgular", "Bilgi bulunamadı."
        )
        tarihsel_onem = bilgi.get(
            "tarihsel_onem", "Bilgi bulunamadı."
        )
        belirsizlikler = bilgi.get(
            "belirsizlikler", "Kesin teşhis değildir."
        )

        genel = (
            f"# 🏛️ {eser_adi}\n\n"
            f"{genel_bakis}\n\n"
            f"### 🌟 Tarihsel Önemi\n{tarihsel_onem}"
        )

        tarihce = (
            "## 📜 Dönem, Uygarlık ve Tarihçe\n\n"
            + tarihce_bilgi
        )

        bulgular = (
            "## 🔎 Arkeolojik Bulgular\n\n"
            + arkeolojik_bulgular
            + "\n\n### ⚠️ Belirsizlikler\n"
            + belirsizlikler
        )

        kaynaklar = (
            "## 📚 Araştırma Kaynakları\n\n"
            "Bu analizde eser özelinde kaynak bağlantıları doğrulanmadı. "
            "Araştırmaya şu genel kaynaklardan başlayabilirsin:\n\n"
            "- [UNESCO Dünya Mirası](https://whc.unesco.org/)\n"
            "- [Türkiye Kültür Portalı](https://www.kulturportali.gov.tr/)\n\n"
            "*Bu bağlantılar genel araştırma kaynaklarıdır; "
            "eserin kimliğini tek başına doğrulamaz.*"
        )

        return genel, tarihce, bulgular, kaynaklar

    except requests.exceptions.Timeout:
        mesaj = "İstek zaman aşımına uğradı. Daha sonra tekrar deneyin."
        return mesaj, mesaj, mesaj, mesaj

    except requests.exceptions.RequestException as hata:
        mesaj = f"Bağlantı hatası: {str(hata)[:300]}"
        return mesaj, mesaj, mesaj, mesaj

    except Exception as hata:
        mesaj = f"Hata: {type(hata).__name__} - {str(hata)[:400]}"
        return mesaj, mesaj, mesaj, mesaj


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
    margin-bottom: 10px;
}
#hero p {
    color: #e0d8c7;
    font-size: 16px;
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

with gr.Blocks(
    title="Tarihinİzi",
    theme=gr.themes.Soft(),
    css=css
) as uygulama:

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

    gr.Markdown(
        "### Yeni bir keşfe hazır mısın?\n"
        "Bir tarihî eser fotoğrafı yükle ve araştırmayı başlat."
    )

    with gr.Group(elem_classes=["panel"]):
        fotograf_girdisi = gr.Image(
            label="Eser fotoğrafı",
            type="filepath",
            height=320
        )
        arastir_butonu = gr.Button(
            "✦  KEŞFİ BAŞLAT",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():
        with gr.Tab("📜 Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Fotoğraf yüklendikten sonra eser tanıtımı burada görünecek."
            )

        with gr.Tab("🏺 Tarihçe"):
            tarihce_cikti = gr.Markdown(
                "Dönem, uygarlık ve tarihsel bağlam burada gösterilecek."
            )

        with gr.Tab("🔎 Arkeolojik Bulgular"):
            bulgu_cikti = gr.Markdown(
                "Görsel analiz detayları burada gösterilecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Araştırma kaynakları burada gösterilecek."
            )

    gr.Markdown(
        "*Tarihinİzi — Yapay zekâ destekli ön araştırma aracı. "
        "Sonuçlar uzman doğrulamasının yerini tutmaz.*"
    )

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[fotograf_girdisi],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            bulgu_cikti,
            kaynak_cikti
        ],
        show_progress="full"
    )

uygulama.launch(share=False)
