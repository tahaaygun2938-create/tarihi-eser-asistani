import os
import io
import json
import base64
import getpass
import requests
import gradio as gr
from PIL import Image

# ==================================================
# AYARLAR
# ==================================================

API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = "gemini-3.5-flash-lite"

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not API_KEY:
    try:
        API_KEY = getpass.getpass("Gemini API anahtarını gir: ").strip()
    except Exception:
        API_KEY = ""

if not API_KEY:
    raise RuntimeError(
        "API anahtarı bulunamadı. GEMINI_API_KEY ortam "
        "değişkenini ayarla veya uygulamayı terminalden çalıştır."
    )


# ==================================================
# MODEL KONTROLÜ
# ==================================================

def model_kontrol():
    try:
        yanit = requests.get(
            f"{API_URL}/models",
            headers={"x-goog-api-key": API_KEY},
            timeout=(5, 15)
        )
        yanit.raise_for_status()
        modeller = yanit.json().get("models", [])

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Model kontrolü zaman aşımına uğradı. "
            "İnternet bağlantını kontrol edip tekrar dene."
        )
    except requests.exceptions.RequestException as hata:
        raise RuntimeError(
            f"Gemini modelleri kontrol edilemedi: {hata}"
        )

    bulunan = next(
        (
            model for model in modeller
            if model.get("name", "").removeprefix("models/") == MODEL_ID
        ),
        None
    )

    if bulunan is None:
        benzerler = [
            model.get("name", "").removeprefix("models/")
            for model in modeller
            if "flash" in model.get("name", "").lower()
        ]

        liste = "\n".join(benzerler[:10]) or "Uygun model bulunamadı."

        raise RuntimeError(
            f"'{MODEL_ID}' bu API anahtarı için listelenmiyor.\n\n"
            f"Kullanılabilir Flash modellerinden bazıları:\n{liste}\n\n"
            "MODEL_ID değerini listelenen ve generateContent "
            "destekleyen bir modelle değiştir."
        )

    if "generateContent" not in bulunan.get(
        "supportedGenerationMethods", []
    ):
        raise RuntimeError(
            f"{MODEL_ID}, generateContent özelliğini desteklemiyor."
        )


model_kontrol()


# ==================================================
# GEMINI İSTEĞİ
# ==================================================

def gemini_istegi(govde):
    url = f"{API_URL}/models/{MODEL_ID}:generateContent"

    try:
        yanit = requests.post(
            url,
            headers={
                "x-goog-api-key": API_KEY,
                "Content-Type": "application/json"
            },
            json=govde,
            timeout=(10, 45)
        )

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Gemini 45 saniye içinde yanıt vermedi. "
            "Daha küçük bir fotoğrafla tekrar dene."
        )

    except requests.exceptions.RequestException as hata:
        raise RuntimeError(f"Bağlantı hatası: {hata}")

    if yanit.status_code == 429:
        raise RuntimeError(
            "Gemini API kotası dolmuş veya istek sınırına ulaşılmış olabilir.\n"
            "Google AI Studio'daki kullanım limitlerini kontrol et.\n\n"
            + yanit.text[:700]
        )

    if yanit.status_code in (401, 403):
        raise RuntimeError(
            "API anahtarı geçersiz olabilir veya bu modele erişim izni yok.\n\n"
            + yanit.text[:700]
        )

    if yanit.status_code == 404:
        raise RuntimeError(
            f"Model bulunamadı: {MODEL_ID}\n\n"
            + yanit.text[:700]
        )

    if not yanit.ok:
        raise RuntimeError(
            f"Gemini HTTP {yanit.status_code}:\n{yanit.text[:1000]}"
        )

    try:
        return yanit.json()
    except ValueError:
        raise RuntimeError("Gemini geçerli bir JSON yanıtı döndürmedi.")


# ==================================================
# ESER ANALİZİ
# ==================================================

def eser_ara(fotograf):
    if fotograf is None:
        return (
            "Önce bir fotoğraf yükle.",
            "",
            "",
            ""
        )

    try:
        # Fotoğrafı küçült ve API için hazırla.
        with Image.open(fotograf) as kaynak:
            im = kaynak.convert("RGB")
            im.thumbnail((1000, 1000))

            tampon = io.BytesIO()
            im.save(tampon, format="JPEG", quality=75, optimize=True)

            foto_data = base64.b64encode(
                tampon.getvalue()
            ).decode("utf-8")

        prompt = """
Sen dikkatli bir arkeoloji ve sanat tarihi araştırma asistanısın.

Fotoğrafı incele ve yalnızca geçerli bir JSON nesnesi döndür.

Şu alanları kullan:
{
  "eser_adi": "Olası eser adı",
  "guven": "Düşük, Orta veya Yüksek ve gerekçesi",
  "genel_bakis": "Fotoğrafta görülen özellikler",
  "tarihce": "Olası dönem ve tarihsel bağlam",
  "arkeolojik_bulgular": "Malzeme, biçim ve süsleme ayrıntıları",
  "tarihsel_onem": "Bilinen önemi veya belirsizlik",
  "belirsizlikler": "Alternatif tanımlamalar ve eksik kanıtlar"
}

Kurallar:
- Türkçe yanıt ver.
- Gözlemleri tahminlerden ayır.
- Emin değilsen bunu açıkça belirt.
- Eserin adını, tarihini veya bulunduğu yeri uydurma.
- Fotoğraftan kesin kimlik tespiti yaptığını iddia etme.
- İncelemediğin kaynakları doğrulanmış gibi gösterme.
- Bilinmeyen bilgileri açıkça belirt.
- JSON dışında açıklama veya Markdown yazma.
"""

        govde = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": foto_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 1800
            }
        }

        sonuc = gemini_istegi(govde)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            engel = sonuc.get("promptFeedback", {}).get(
                "blockReason", "Belirtilmedi"
            )
            raise RuntimeError(
                f"Model analiz sonucu üretmedi. Engel nedeni: {engel}"
            )

        aday = adaylar[0]
        parcalar = aday.get("content", {}).get("parts", [])

        metin = "\n".join(
            parca.get("text", "")
            for parca in parcalar
            if parca.get("text")
        ).strip()

        if not metin:
            bitis = aday.get("finishReason", "Bilinmiyor")
            raise RuntimeError(
                f"Model boş yanıt verdi. Bitiş nedeni: {bitis}"
            )

        # Olası Markdown işaretlerini temizle.
        if metin.startswith("```"):
            satirlar = metin.splitlines()
            if satirlar and satirlar[0].startswith("```"):
                satirlar = satirlar[1:]
            if satirlar and satirlar[-1].strip() == "```":
                satirlar = satirlar[:-1]
            metin = "\n".join(satirlar).strip()

        try:
            bilgi = json.loads(metin)
        except json.JSONDecodeError:
            raise RuntimeError(
                "Model yanıtı geçerli JSON biçiminde değil. "
                "Lütfen fotoğrafı tekrar deneyin."
            )

        def alan(ad, varsayilan):
            deger = bilgi.get(ad, varsayilan)
            if deger is None:
                return varsayilan
            if isinstance(deger, (dict, list)):
                return json.dumps(deger, ensure_ascii=False, indent=2)
            return str(deger).strip() or varsayilan

        eser = alan("eser_adi", "Tanımlanamayan eser")
        guven = alan("guven", "Belirlenemedi")
        genel = alan("genel_bakis", "Bilgi bulunamadı.")
        tarih = alan("tarihce", "Tarihçe kesinleştirilemedi.")
        bulgu = alan("arkeolojik_bulgular", "Bulgu belirtilmedi.")
        onem = alan("tarihsel_onem", "Önemi kesinleştirilemedi.")
        belirsizlik = alan("belirsizlikler", "Belirsizlik belirtilmedi.")

        genel_cikti = (
            f"# 🏛️ {eser}\n\n"
            f"**Tahmini güven düzeyi:** {guven}\n\n"
            f"### 📝 Genel tanıtım\n{genel}\n\n"
            f"### 🌟 Tarihsel önemi\n{onem}"
        )

        tarih_cikti = (
            f"## 📜 Dönem, uygarlık ve tarihçe\n\n"
            f"{tarih}\n\n"
            "Bu değerlendirme bağımsız kaynaklarla doğrulanmalıdır."
        )

        bulgu_cikti = (
            f"## 🔎 Arkeolojik bulgular\n\n{bulgu}\n\n"
            f"### ⚠️ Belirsizlikler\n{belirsizlik}"
        )

        kaynak_cikti = """
## 📚 Kaynak kontrolü

Bu analiz sırasında belirli eser kayıtları bağımsız olarak doğrulanmadı.
Araştırmaya başlamak için aşağıdaki kaynakları kullanabilirsin:

- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [T.C. Kültür Portalı](https://www.kulturportali.gov.tr/)

Bu bağlantılar, analiz edilen eserin bu kaynaklarda kayıtlı olduğunu
tek başına kanıtlamaz.

*Bu sonuç bir ön değerlendirmedir; uzman incelemesinin yerini tutmaz.*
"""

        return (
            genel_cikti,
            tarih_cikti,
            bulgu_cikti,
            kaynak_cikti
        )

    except Exception as hata:
        mesaj = str(hata)
        print("ESER ANALİZ HATASI:", repr(hata))

        return (
            f"## ⚠️ Analiz tamamlanamadı\n\n{mesaj}",
            "Tarihçe üretilemedi.",
            "Bulgular üretilemedi.",
            "Bu denemede kaynak doğrulaması yapılmadı."
        )


# ==================================================
# TASARIM
# ==================================================

css = """
.gradio-container {
    max-width: 1100px !important;
    margin: auto !important;
    background: #101114 !important;
    color: #f5f0e6 !important;
}

#hero {
    position: relative;
    padding: 42px 22px;
    border-radius: 22px;
    text-align: center;
    background: linear-gradient(135deg, #202321, #17151b, #292116);
    border: 1px solid #806b40;
}

#hero h1 {
    color: #e5c47a;
    font-size: clamp(28px, 5vw, 46px);
    text-shadow: 0 0 12px #806b40;
}

#hero p {
    color: #e0d8c7;
}

.gold-line {
    height: 2px;
    width: 65%;
    margin: 22px auto;
    background
