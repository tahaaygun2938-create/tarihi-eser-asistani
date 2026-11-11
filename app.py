import os
import io
import json
import time
import base64
import requests
import gradio as gr

from PIL import Image

# ==========================================
# AYARLAR
# ==========================================

API_URL = "https://generativelanguage.googleapis.com/v1beta"

MODEL_ID = os.environ.get(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
).strip()

MAX_IMAGE_SIZE = (1400, 1400)
MAX_RETRIES = 4


# ==========================================
# FOTOĞRAF İŞLEME
# ==========================================

def fotograf_isle(dosya_yolu):

    if not dosya_yolu:
        raise gr.Error("Lütfen önce bir fotoğraf yükle.")

    try:
        with Image.open(dosya_yolu) as img:

            img = img.convert("RGB")
            img.thumbnail(MAX_IMAGE_SIZE)

            buffer = io.BytesIO()

            img.save(
                buffer,
                format="JPEG",
                quality=90,
                optimize=True
            )

            return base64.b64encode(
                buffer.getvalue()
            ).decode("utf-8")

    except Exception as e:
        raise gr.Error(
            f"Fotoğraf işlenemedi: {str(e)}"
        )


# ==========================================
# GEMINI API İSTEĞİ
# ==========================================

def gemini_istegi(fotograf_base64, ek_bilgi=""):

    api_key = os.environ.get(
        "GEMINI_API_KEY",
        ""
    ).strip()

    if not api_key:
        raise gr.Error(
            "GEMINI_API_KEY bulunamadı. "
            "Render Environment ayarlarını kontrol et."
        )

    url = (
        f"{API_URL}/models/"
        f"{MODEL_ID}:generateContent"
    )

    prompt = f"""
Sen tarih, arkeoloji, sanat tarihi ve mimarlık
alanlarında çalışan dikkatli bir araştırma asistanısın.

Görevin, kullanıcının yüklediği fotoğrafı inceleyerek
fotoğraftaki tarihî eseri tanımlamak ve kapsamlı
bilimsel açıklamalar oluşturmaktır.

KULLANICI EK BİLGİSİ:
{ek_bilgi if ek_bilgi.strip() else "Ek bilgi verilmedi."}

ÖNEMLİ KURALLAR:

1. Fotoğrafta gerçekten görülen özellikleri incele.
2. Eserin kimliğinden emin değilsen kesin konuşma.
3. Birbirine benzeyen tarihî yapıları birbirine karıştırma.
4. Bilmediğin tarihleri, olayları ve arkeolojik bulguları uydurma.
5. Kesin bilgiler ile tahminleri birbirinden ayır.
6. Fotoğraftan anlaşılamayan özellikleri açıkça belirt.
7. Kaynak olarak emin olmadığın makale, kitap veya bağlantıları uydurma.
8. Yanlış bir tanımlama yapmaktansa belirsizliği belirt.
9. Cevaplarını Türkçe hazırla.
10. Mümkün olduğunca ayrıntılı fakat anlaşılır bilgiler ver.

Aşağıdaki JSON yapısını eksiksiz doldur:

{{
    "eser_adi": "",
    "guven": "",
    "genel_bakis": "",
    "tarihce": "",
    "medeniyet": "",
    "donem": "",
    "konum": "",
    "mimari_ozellikler": "",
    "yapim_malzemeleri": "",
    "yapim_teknikleri": "",
    "sanatsal_ozellikler": "",
    "semboller_ve_suslemeler": "",
    "kullanim_amaci": "",
    "arkeolojik_bulgular": "",
    "tarihsel_onem": "",
    "toplumsal_ve_kulturel_yasam": "",
    "benzer_eserler": "",
    "korunma_durumu": "",
    "tarihsel_olaylar": "",
    "bilimsel_degerlendirme": "",
    "belirsizlikler": "",
    "alternatif_tanimlamalar": "",
    "dogrulanmasi_gerekenler": "",
    "kaynak_onerileri": ""
}}

Güven alanında yüzde değeri ver.
Bu değerin bilimsel olarak ölçülmüş bir doğruluk oranı
değil, modelin tahmin güvenini yansıttığını unutma.

Yalnızca geçerli JSON döndür.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": fotograf_base64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 6000,
            "responseMimeType": "application/json"
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=180
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code in [
                429, 500, 502, 503, 504
            ]:

                if attempt < MAX_RETRIES - 1:

                    bekleme = 2 ** (attempt + 1)

                    time.sleep(bekleme)
                    continue

                if response.status_code == 429:
                    raise gr.Error(
                        "Gemini kullanım kotası dolmuş "
                        "veya istek sınırına ulaşılmış. "
                        "Bir süre sonra tekrar dene."
                    )

                if response.status_code == 503:
                    raise gr.Error(
                        "Gemini sunucuları şu anda yoğun. "
                        "Bir süre sonra tekrar dene."
                    )

                raise gr.Error(
                    f"Gemini HTTP {response.status_code}: "
                    "Sunucu isteği işleyemedi. "
                    "Daha sonra tekrar dene."
                )

            if response.status_code in [401, 403]:
                raise gr.Error(
                    "API anahtarı geçersiz veya erişim izni yok. "
                    "Google AI Studio ve Render ayarlarını kontrol et."
                )

            if response.status_code == 400:
                raise gr.Error(
                    "Gemini isteği kabul etmedi. "
                    "Model adını ve API isteğini kontrol et.\n"
                    + response.text[:1000]
                )

            if response.status_code == 404:
                raise gr.Error(
                    f"{MODEL_ID} modeli bulunamadı. "
                    "Google AI Studio'daki model erişimini kontrol et."
                )

            raise gr.Error(
                f"Gemini HTTP {response.status_code}: "
                + response.text[:1000]
            )

        except requests.exceptions.Timeout:

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            raise gr.Error(
                "Gemini isteği zaman aşımına uğradı."
            )

        except requests.exceptions.RequestException as e:

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue

            raise gr.Error(
                f"İnternet bağlantısı hatası: {str(e)}"
            )

    raise gr.Error("Analiz tamamlanamadı.")


# ==========================================
# JSON SONUÇLARINI AYRIŞTIRMA
# ==========================================

def json_ayristir(veri):

    try:

        metin = veri["candidates"][0]["content"]["parts"][0]["text"]

        metin = metin.strip()

        if metin.startswith("```"):
            metin = metin.replace("```json", "", 1)
            metin = metin.replace("```", "").strip()

        baslangic = metin.find("{")
        bitis = metin.rfind("}")

        if baslangic == -1 or bitis == -1:
            raise ValueError("JSON bulunamadı.")

        return json.loads(
            metin[baslangic:bitis + 1]
        )

    except Exception as e:

        raise gr.Error(
            "Yapay zekâ cevabı okunamadı. "
            f"Hata: {str(e)}"
        )


# ==========================================
# ANA ANALİZ FONKSİYONU
# ==========================================

def eser_ara(fotograf, ek_bilgi):

    if not fotograf:
        raise gr.Error("Lütfen bir fotoğraf yükle.")

    gr.Info("Fotoğraf analiz ediliyor...")

    fotograf_base64 = fotograf_isle(fotograf)

    cevap = gemini_istegi(
        fotograf_base64,
        ek_bilgi or ""
    )

    sonuc = json_ayristir(cevap)

    def al(alan):
        return str(
            sonuc.get(alan, "Bu bilgi belirlenemedi.")
        )

    return (
        al("eser_adi"),
        al("guven"),
        al("genel_bakis"),
        al("tarihce"),
        al("medeniyet") + "\n\n" + al("donem") + "\n\n" + al("konum"),
        al("mimari_ozellikler") + "\n\n" + al("yapim_malzemeleri") + "\n\n" + al("yapim_teknikleri"),
        al("sanatsal_ozellikler") + "\n\n" + al("semboller_ve_suslemeler") + "\n\n" + al("kullanim_amaci"),
        al("arkeolojik_bulgular") + "\n\n" + al("korunma_durumu"),
        al("tarihsel_onem") + "\n\n" + al("tarihsel_olaylar") + "\n\n" + al("toplumsal_ve_kulturel_yasam"),
        al("benzer_eserler"),
        al("bilimsel_degerlendirme") + "\n\n" + al("belirsizlikler") + "\n\n" + al("alternatif_tanimlamalar") + "\n\n" + al("dogrulanmasi_gerekenler"),
        al("kaynak_onerileri")
    )


# ==========================================
# TASARIM
# ==========================================

CSS = """
.gradio-container {
    background: #101114 !important;
    color: #eeeeee !important;
    max-width: 1200px !important;
    margin: auto !important;
}

body {
    background: #101114 !important;
}

h1, h2, h3 {
    color: #eeeeee !important;
}

.title {
    text-align: center;
    padding: 22px 10px;
}

.title h1 {
    font-size: 32px;
    letter-spacing: 2px;
    font-weight: 800;
}

.title p {
    color: #a5a5a5;
    font-size: 15px;
}

button.primary {
    background: #34363d !important;
    border: 1px solid #555862 !important;
    color: white !important;
}

button.primary:hover {
    background: #454852 !important;
}

textarea, input {
    background: #191b20 !important;
    color: #eeeeee !important;
    border-color: #34363d !important;
}

footer {
    display: none !important;
}
"""


# ==========================================
# ARAYÜZ
# ==========================================

with gr.Blocks(
    title="Tarihinİzi",
    css=CSS,
    theme=gr.themes.Base()
) as demo:

    gr.HTML("""
    <div class="title">
        <h1>TARİHİN İZİNİ SÜR</h1>
        <p>Yapay zekâ destekli tarihî eser tanıma asistanı</p>
    </div>
    """)

    with gr.Row():

        with gr.Column(scale=1):

            fotograf = gr.Image(
                label="Tarihî Eser Fotoğrafı",
                type="filepath",
                height=350
            )

            ek_bilgi = gr.Textbox(
                label="Ek Bilgi (İsteğe Bağlı)",
                placeholder="Örneğin: Bu yapı Van'da bulunuyor olabilir.",
                lines=3
            )

            analiz_butonu = gr.Button(
                "✦ KEŞFİ BAŞLAT",
                variant="primary",
                size="lg"
            )

        with gr.Column(scale=1):

            eser_adi = gr.Textbox(
                label="Eserin Adı",
                interactive=False
            )

            guven = gr.Textbox(
                label="Yapay Zekâ Tahmin Güveni",
                interactive=False
            )

            genel = gr.Textbox(
                label="Genel Bakış",
                lines=8,
                interactive=False
            )

    with gr.Tabs():

        with gr.Tab("Tarih ve Medeniyet"):

            tarihce = gr.Textbox(
                label="Tarihçe",
                lines=12,
                interactive=False
            )

            medeniyet = gr.Textbox(
                label="Medeniyet, Dönem ve Konum",
                lines=8,
                interactive=False
            )

        with gr.Tab("Mimari ve Arkeoloji"):

            mimari = gr.Textbox(
                label="Mimari Özellikler ve Yapım Teknikleri",
                lines=12,
                interactive=False
            )

            arkeoloji = gr.Textbox(
                label="Arkeolojik Bulgular ve Korunma",
                lines=10,
                interactive=False
            )

        with gr.Tab("Sanat ve Kullanım"):

            sanat = gr.Textbox(
                label="Sanatsal Özellikler ve Kullanım Amacı",
                lines=12,
                interactive=False
            )

            benzer = gr.Textbox(
                label="Benzer Eserler",
                lines=6,
                interactive=False
            )

        with gr.Tab("Tarihsel Önem"):

            onem = gr.Textbox(
                label="Tarihsel ve Kültürel Önem",
                lines=12,
                interactive=False
            )

        with gr.Tab("Bilimsel Değerlendirme"):

            degerlendirme = gr.Textbox(
                label="Belirsizlikler ve Doğrulanması Gerekenler",
                lines=14,
                interactive=False
            )

        with gr.Tab("Kaynaklar"):

            kaynaklar = gr.Textbox(
                label="Kaynak Önerileri",
                lines=10,
                interactive=False
            )

    gr.HTML("""
    <div style="
        text-align:center;
        color:#777;
        padding:20px;
        font-size:12px;">
        Tarihinİzi | by Taha Anıl Aygün
    </div>
    """)

    ciktilar = [
        eser_adi,
        guven,
        genel,
        tarihce,
        medeniyet,
        mimari,
        sanat,
        arkeoloji,
        onem,
        benzer,
        degerlendirme,
        kaynaklar
    ]

    analiz_butonu.click(
        fn=eser_ara,
        inputs=[fotograf, ek_bilgi],
        outputs=ciktilar
    )


# ==========================================
# UYGULAMAYI BAŞLAT
# ==========================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port
    )
