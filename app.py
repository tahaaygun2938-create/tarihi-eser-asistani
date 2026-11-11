
import os
import io
import json
import time
import base64
import requests
import gradio as gr
from PIL import Image

# =========================================================
# AYARLAR
# =========================================================

API_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MAX_IMAGE_SIZE = (1600, 1600)
MAX_OUTPUT_TOKENS = 12000
MAX_RETRIES = 4

# =========================================================
# UYGULAMA BAŞLIKLARI VE ALT BAŞLIKLAR
# =========================================================

SECTIONS = {
    "genel_bakis": {
        "title": "Genel Bakış",
        "subsections": {
            "eserin_tanimi": "Eserin Tanımı ve Genel Özellikleri",
            "kimlik_bilgileri": "Kimlik Bilgileri ve Sınıflandırma",
            "tarihsel_konum": "Tarihsel ve Coğrafi Konum",
            "genel_degerlendirme": "Genel Tarihsel Değerlendirme"
        }
    },
    "tarih_ve_medeniyet": {
        "title": "Tarih ve Medeniyet",
        "subsections": {
            "ortaya_cikis": "Ortaya Çıkışı ve Kuruluş Süreci",
            "tarihsel_arka_plan": "Dönemin Tarihsel Arka Planı",
            "medeniyet": "Medeniyet ve Kültürel Çevre",
            "yonetim": "Siyasi Yapı ve Yönetim",
            "tarihsel_olaylar": "Eserle İlişkili Tarihsel Olaylar",
            "zaman_cizelgesi": "Kronolojik Gelişim"
        }
    },
    "mimari": {
        "title": "Mimari ve Yapım Teknikleri",
        "subsections": {
            "mimari_plan": "Mimari Plan ve Yerleşim Düzeni",
            "yapi_ozellikleri": "Yapısal ve Mimari Özellikler",
            "malzemeler": "Kullanılan Yapı Malzemeleri",
            "teknikler": "İnşa Teknikleri ve Mühendislik",
            "stil": "Mimari Üslup ve Benzer Yapılar",
            "degisim": "Tarih İçinde Geçirdiği Mimari Değişimler"
        }
    },
    "arkeoloji": {
        "title": "Arkeoloji ve Bulgular",
        "subsections": {
            "kazilar": "Arkeolojik Kazılar ve Araştırmalar",
            "buluntular": "Ortaya Çıkarılan Arkeolojik Bulgular",
            "yazitlar": "Yazıtlar, Kitabeler ve Belgeler",
            "arkeolojik_yorum": "Buluntuların Bilimsel Yorumu",
            "koruma": "Korunma Durumu ve Restorasyon Çalışmaları"
        }
    },
    "sanat_ve_semboller": {
        "title": "Sanat, Süsleme ve Semboller",
        "subsections": {
            "sanatsal_ozellikler": "Sanatsal Özellikler",
            "suslemeler": "Süslemeler ve Dekoratif Unsurlar",
            "semboller": "Semboller ve Motiflerin Anlamları",
            "sanat_tarihi": "Sanat Tarihindeki Yeri",
            "etkilesimler": "Diğer Kültürlerle Sanatsal Etkileşim"
        }
    },
    "kullanim_ve_yasam": {
        "title": "Kullanım Amacı ve Günlük Yaşam",
        "subsections": {
            "ilk_kullanim": "İlk Kullanım Amacı",
            "gunluk_yasam": "Günlük Yaşam ve Toplumsal Hayat",
            "dini_rituel": "Dini, Kültürel veya Törensel İşlevler",
            "ekonomi": "Ekonomik ve Ticari Hayattaki Yeri",
            "toplumsal_yapi": "Toplumsal Yapı ve İnsan İlişkileri"
        }
    },
    "tarihsel_onem": {
        "title": "Tarihsel Önemi ve Etkileri",
        "subsections": {
            "bolgesel_onem": "Bölgesel Tarih Açısından Önemi",
            "dunya_tarihi": "Dünya Tarihi Açısından Önemi",
            "siyasi_etki": "Siyasi ve Askerî Etkileri",
            "kulturel_etki": "Kültürel ve Medeniyet Tarihine Etkileri",
            "miras": "Günümüze Bıraktığı Tarihî Miras"
        }
    },
    "karsilastirma": {
        "title": "Karşılaştırmalı İnceleme",
        "subsections": {
            "benzer_eserler": "Benzer Tarihî Eserler",
            "farkliliklar": "Benzer Eserlerle Farklılıkları",
            "donem_karsilastirma": "Dönemindeki Diğer Yapılarla Karşılaştırma",
            "ozgunluk": "Eserin Özgün ve Ayırt Edici Yönleri"
        }
    },
    "bilimsel_degerlendirme": {
        "title": "Bilimsel Değerlendirme",
        "subsections": {
            "tarihsel_yorum": "Tarihsel Değerlendirme",
            "arkeolojik_yorum": "Arkeolojik ve Bilimsel Yorum",
            "guvenilirlik": "Bilgilerin Güvenilirliği",
            "belirsizlikler": "Belirsiz ve Tartışmalı Noktalar",
            "alternatifler": "Alternatif Tanımlamalar",
            "arastirma_ihtiyaclari": "Daha Fazla Araştırılması Gereken Konular"
        }
    },
    "kaynaklar": {
        "title": "Kaynaklar ve İleri Okuma",
        "subsections": {
            "akademik_kaynaklar": "Akademik Kaynak Önerileri",
            "kitaplar": "Kitap ve Araştırma Eserleri",
            "kurumlar": "Müze, Üniversite ve Kurum Kaynakları",
            "kaynak_notu": "Kaynak Kullanımı ve Doğrulama Notu"
        }
    }
}


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def resmi_hazirla(image):
    """Görseli Gemini API için JPEG formatına dönüştürür."""

    if image is None:
        raise ValueError("Lütfen önce bir tarihî eser fotoğrafı yükle.")

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.thumbnail(MAX_IMAGE_SIZE)

    if image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)

    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return encoded


def beklenen_yapiyi_olustur():
    """Gemini'den istenecek JSON yapısını hazırlar."""

    structure = {}

    for section_key, section in SECTIONS.items():
        structure[section_key] = {}

        for subsection_key in section["subsections"]:
            structure[section_key][subsection_key] = (
                "Bu alt başlığın kapsamlı açıklaması"
            )

    return structure


def json_ayristir(text):
    """Gemini cevabındaki JSON verisini ayıklar."""

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])

        raise ValueError("Yapay zekâdan geçerli JSON cevabı alınamadı.")


def metni_temizle(value):
    """Gelen metni güvenli biçimde düzenler."""

    if value is None:
        return "Bu konuda yeterli bilgi bulunamadı."

    if isinstance(value, list):
        return "\n\n".join(
            str(item) for item in value if item
        )

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )

    return str(value).strip()


# =========================================================
# GEMINI İSTEMİ
# =========================================================

def prompt_olustur():

    expected = beklenen_yapiyi_olustur()

    return f"""
Sen deneyimli bir tarihçi, arkeolog, sanat tarihçisi ve kültürel
miras araştırmacısı gibi çalışan bir tarihî eser analiz sistemisin.

Görevin, kullanıcının yüklediği fotoğrafı incelemek ve fotoğraftaki
tarihî eseri mümkün olduğunca kapsamlı biçimde analiz etmektir.

ÇOK ÖNEMLİ: KISA CEVAP VERME.

Bu uygulamanın amacı birkaç cümlelik tanıtım yazısı oluşturmak değil,
kullanıcıya kapsamlı bir dijital tarih ansiklopedisi sunmaktır.

GENEL YAZIM KURALLARI:

1. Her ana başlığın altındaki TÜM alt başlıkları doldur.
2. Hiçbir alt başlığı boş bırakma.
3. Her alt başlıkta en az 2-3 ayrıntılı paragraf yaz.
4. Paragrafları açıklayıcı, tarihsel ve akademik bir dille oluştur.
5. Uygun olduğu yerlerde tarihleri, dönemleri, hükümdarları,
   devletleri, uygarlıkları ve tarihsel olayları belirt.
6. Bir olaydan bahsederken yalnızca ne olduğunu değil,
   neden gerçekleştiğini ve sonuçlarını da açıkla.
7. Mimari özellikleri anlatırken yapının bölümlerini,
   malzemelerini, yapım tekniklerini ve işlevlerini ayrı ayrı incele.
8. Arkeolojik bulguları anlatırken buluntunun ne olduğunu,
   neyi gösterdiğini ve tarihçiler açısından neden önemli
   olduğunu açıkla.
9. Benzer eserleri yalnızca isim olarak sıralama.
   Benzerliklerini ve farklılıklarını açıkla.
10. Tarihsel bilgileri birbirine bağla. Konuları yüzeysel geçme.
11. Kullanıcıya bilinmeyen terimleri açıklayarak anlat.
12. Aynı bilgiyi farklı alt başlıklarda gereksiz yere tekrarlama.
13. Fotoğraftan kesin olarak anlaşılamayan ayrıntıları kesin bilgi
    gibi sunma.
14. Bilmediğin tarihleri, hükümdarları, kazı sonuçlarını,
    kitabeleri veya akademik kaynakları uydurma.
15. Kesin bilgi, güçlü ihtimal ve belirsiz bilgileri birbirinden ayır.
16. Eserin fotoğraftan tanımlanması mümkün değilse bunu açıkça belirt.
17. Eserin konumunu ve kimliğini belirlerken birden fazla ihtimali
    değerlendir.
18. Kaynak önerilerinde gerçekliğinden emin olmadığın kitap,
    makale, yazar veya bağlantıları uydurma. Kaynak doğrulanamıyorsa
    bunu açıkça söyle.

UZUNLUK TALİMATI:

- Her alt başlık için hedef olarak 150-250 kelime yaz.
- Önemli tarihsel konularda daha uzun açıklamalar yap.
- Her alt başlıkta yalnızca tanım vermekle yetinme.
- Neden-sonuç ilişkileri, tarihsel arka plan ve örnekler ekle.
- Toplam cevap kapsamlı bir araştırma dosyası niteliğinde olsun.
- Token sınırına yaklaştığında alt başlıkları tamamen atlamak yerine
  bütün başlıklara dengeli biçimde yer ver.

ESERİN KİMLİĞİ:

Önce fotoğraftaki eserin ne olduğunu belirle.
Eğer kesin tanımlama yapılamıyorsa en olası tanımlamayı ve
alternatif ihtimalleri belirt.

GÜVEN DEĞERİ:

0 ile 100 arasında bir güven değeri ver.
Bu değer bilimsel olarak ölçülmüş bir doğruluk oranı değildir.
Yalnızca fotoğrafa dayalı tanımlamanın güven düzeyini ifade eder.

ÇIKTI BİÇİMİ:

Yalnızca geçerli JSON döndür.
Markdown kod bloğu kullanma.
JSON dışında açıklama yazma.

JSON yapısı:

{{
  "eser_adi": "Eserin adı veya en olası tanımlaması",
  "guven": 0,
  "kimliklendirme_notu": "Tanımlamanın hangi görsel özelliklere dayandığı",
  "bolumler": {json.dumps(expected, ensure_ascii=False)}
}}

Bütün anahtarları koru.
Her alt başlığın değerini kapsamlı Türkçe açıklamalarla doldur.
"""


# =========================================================
# GEMINI API
# =========================================================

def gemini_analiz(image):

    if not API_KEY:
        raise ValueError(
            "GEMINI_API_KEY bulunamadı. "
            "Render Environment bölümünü kontrol et."
        )

    image_base64 = resmi_hazirla(image)

    url = (
        f"{API_URL}/models/{MODEL_ID}:generateContent"
        f"?key={API_KEY}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_olustur()
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "responseMimeType": "application/json"
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    last_error = None

    for attempt in range(MAX_RETRIES):

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=240
            )

            if response.status_code == 200:
                result = response.json()

                candidates = result.get("candidates", [])

                if not candidates:
                    raise ValueError(
                        "Gemini boş cevap verdi. "
                        "Fotoğrafı tekrar deneyebilirsin."
                    )

                parts = candidates[0].get(
                    "content", {}
                ).get("parts", [])

                answer = "".join(
                    part.get("text", "")
                    for part in parts
                )

                if not answer.strip():
                    raise ValueError(
                        "Gemini analiz metni döndürmedi."
                    )

                return json_ayristir(answer)

            if response.status_code in (429, 500, 502, 503, 504):
                last_error = response.text

                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** (attempt + 1))
                    continue

            elif response.status_code in (401, 403):
                raise ValueError(
                    "API anahtarı geçersiz veya API erişiminde "
                    "yetki sorunu var. Render Environment "
                    "ayarlarını kontrol et."
                )

            elif response.status_code == 404:
                raise ValueError(
                    f"{MODEL_ID} modeli bulunamadı. "
                    "GEMINI_MODEL değerini kontrol et."
                )

            else:
                raise ValueError(
                    f"Gemini API hatası ({response.status_code}): "
                    f"{response.text[:1000]}"
                )

        except requests.exceptions.Timeout:
            last_error = "İstek zaman aşımına uğradı."

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue

        except requests.exceptions.RequestException as error:
            last_error = str(error)

            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue

    raise ValueError(
        "Gemini şu anda ayrıntılı analiz oluşturamadı. "
        "Bir süre sonra tekrar dene.\n\n"
        f"Teknik bilgi: {str(last_error)[:1000]}"
    )


# =========================================================
# SONUÇLARI EKRANA YAZDIRMA
# =========================================================

def markdown_olustur(analysis, section_key):

    sections = analysis.get("bolumler", {})
    section_data = sections.get(section_key, {})

    section = SECTIONS[section_key]

    output = []

    for subsection_key, subsection_title in (
        section["subsections"].items()
    ):

        content = section_data.get(subsection_key)

        output.append(f"## {subsection_title}\n")

        if content:
            output.append(metni_temizle(content))
        else:
            output.append(
                "Bu alt başlık için yeterli bilgi oluşturulamadı."
            )

        output.append("\n\n---\n")

    return "\n".join(output)


def kaynaklari_duzenle(analysis):

    section_data = analysis.get(
        "bolumler", {}
    ).get("kaynaklar", {})

    output = []

    for key, title in SECTIONS["kaynaklar"]["subsections"].items():

        content = section_data.get(key)

        output.append(f"## {title}\n")

        if content:
            output.append(metni_temizle(content))
        else:
            output.append(
                "Bu konuda kaynak bilgisi oluşturulamadı."
            )

        output.append("\n\n---\n")

    output.append(
        "\n**Önemli not:** Bu bölümde sunulan kaynak önerileri "
        "kullanılmadan önce akademik kataloglar, üniversiteler, "
        "müzeler veya yayıncılar üzerinden doğrulanmalıdır. "
        "Yapay zekâ tarafından önerilen bir kaynak otomatik "
        "olarak doğrulanmış kaynak anlamına gelmez."
    )

    return "\n".join(output)


# =========================================================
# ANALİZ FONKSİYONU
# =========================================================

def analiz_et(image):

    if image is None:
        return (
            "<span style='color:#ff7777'>Önce bir fotoğraf yüklemelisin.</span>",
            *[""] * len(SECTIONS)
        )

    try:
        analysis = gemini_analiz(image)

        eser_adi = analysis.get(
            "eser_adi",
            "Tanımlama yapılamadı"
        )

        guven = analysis.get("guven", 0)
        not_text = analysis.get(
            "kimliklendirme_notu",
            ""
        )

        try:
            guven = max(0, min(100, int(guven)))
        except (ValueError, TypeError):
            guven = 0

        status = f"""
# {eser_adi}

**Görsel Tanımlama Güveni:** %{guven}

{not_text}

---

<small>
Bu güven değeri bilimsel olarak ölçülmüş bir başarı oranı değil,
fotoğrafa dayalı tahmini tanımlama güvenidir.
</small>
"""

        results = []

        for section_key in SECTIONS:
            results.append(
                markdown_olustur(analysis, section_key)
            )

        return (status, *results)

    except Exception as error:

        error_message = f"""
### Analiz sırasında hata oluştu

{str(error)}

Lütfen tekrar dene. Sorun devam ederse Render Logs bölümündeki
teknik hata mesajını kontrol et.
"""

        return (
            error_message,
            *[""] * len(SECTIONS)
        )


# =========================================================
# GRADIO TASARIMI
# =========================================================

CSS = """
body, .gradio-container {
    background: #101114 !important;
    color: #e8e8e8 !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}

h1, h2, h3 {
    color: #eeeeee !important;
}

.tabs {
    border-color: #303238 !important;
}

button.primary {
    background: #34363d !important;
    border: 1px solid #555861 !important;
    color: white !important;
}

button.primary:hover {
    background: #444750 !important;
}

textarea, input {
    background: #191a1f !important;
}

.prose, .markdown {
    color: #dddddd !important;
}

footer {
    visibility: hidden;
}
"""


with gr.Blocks(
    theme=gr.themes.Base(),
    css=CSS,
    title="Tarihinİzi"
) as demo:

    gr.Markdown(
        """
# TARİHİNİZİ SÜR

### Tarihî Eser Asistanı

Bir tarihî eser fotoğrafı yükle. Yapay zekâ ile eserin
tarihçesini, mimarisini, arkeolojik bulgularını ve
medeniyetler içindeki yerini ayrıntılı biçimde incele.
"""
    )

    with gr.Row():

        with gr.Column(scale=1):

            image_input = gr.Image(
                label="Tarihî Eser Fotoğrafı",
                type="pil",
                height=350
            )

            analyze_button = gr.Button(
                "✦ KEŞFİ BAŞLAT",
                variant="primary"
            )

            status_output = gr.Markdown(
                label="Eser Tanımlaması"
            )

    gr.Markdown("---")

    gr.Markdown(
        """
## ARAŞTIRMA DOSYASI

Aşağıdaki sekmelerde esere ilişkin ayrıntılı tarihsel
ve bilimsel incelemeyi bulabilirsin.
"""
    )

    outputs = []

    with gr.Tabs():

        for section_key, section in SECTIONS.items():

            with gr.Tab(section["title"]):

                output = gr.Markdown(
                    value=(
                        "Henüz analiz yapılmadı. "
                        "Bir fotoğraf yükleyip keşfi başlat."
                    )
                )

                outputs.append(output)

    analyze_button.click(
        fn=analiz_et,
        inputs=[image_input],
        outputs=[status_output] + outputs
    )

    gr.Markdown(
        """
---

<small>
**Tarihinİzi** | by Taha Anıl Aygün
</small>
"""
    )


# =========================================================
# UYGULAMAYI BAŞLAT
# =========================================================

if __name__ == "__main__":

    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860))
    )
