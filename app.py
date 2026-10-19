import os
import io
import json
import base64
import requests
import gradio as gr
from PIL import Image


# =====================================================
# AYARLAR
# =====================================================

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL_ID = "gemini-3.5-flash-lite"
API_URL = "https://generativelanguage.googleapis.com/v1beta"

TIMEOUT = 90


# =====================================================
# GEMINI API İSTEGI
# =====================================================

def gemini_istegi(fotograf_base64, prompt):
    if not API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadi. "
            "Render Environment bolumune API anahtarini ekle."
        )

    url = (
        f"{API_URL}/models/"
        f"{MODEL_ID}:generateContent"
    )

    body = {
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
            "temperature": 0.25,
            "maxOutputTokens": 6000,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": API_KEY
            },
            json=body,
            timeout=(10, TIMEOUT)
        )

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Gemini yaniti zaman asimina ugradi. "
            "Daha kucuk bir fotografla tekrar dene."
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Baglanti hatasi: {error}"
        )

    if response.status_code != 200:
        try:
            detail = response.json().get(
                "error", {}
            ).get("message", response.text[:600])
        except (ValueError, AttributeError):
            detail = response.text[:600]

        if response.status_code == 429:
            raise RuntimeError(
                "API kullanim limiti asildi. Bir sure bekle.\n"
                + detail
            )

        if response.status_code in (401, 403):
            raise RuntimeError(
                "API anahtari veya erisim izni sorunu.\n"
                + detail
            )

        if response.status_code == 404:
            raise RuntimeError(
                f"Model bulunamadi: {MODEL_ID}\n"
                + detail
            )

        raise RuntimeError(
            f"Gemini HTTP {response.status_code}\n{detail}"
        )

    result = response.json()
    candidates = result.get("candidates", [])

    if not candidates:
        feedback = result.get("promptFeedback", {})
        raise RuntimeError(
            "Model yanit olusturmadi. "
            + str(feedback.get("blockReason", "Neden belirtilmedi"))
        )

    parts = candidates[0].get(
        "content", {}
    ).get("parts", [])

    answer = "\n".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not answer:
        reason = candidates[0].get(
            "finishReason", "Bilinmiyor"
        )
        raise RuntimeError(
            f"Model bos yanit verdi. Bitis nedeni: {reason}"
        )

    return answer


# =====================================================
# DETAYLI ESER ARASTIRMASI
# =====================================================

def eser_ara(fotograf, arastirma_turu, ek_bilgi):
    if not fotograf:
        return (
            "Once bir eser fotografi yukle.",
            "", "", "", "", "", ""
        )

    try:
        # Fotograf dosyasini optimize et
        with Image.open(fotograf) as original:
            image = original.convert("RGB")
            image.thumbnail((1100, 1100))

            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=82,
                optimize=True
            )

            image_base64 = base64.b64encode(
                buffer.getvalue()
            ).decode("utf-8")

        prompt = """
Sen bir arkeoloji, sanat tarihi, eski uygarliklar,
maddi kultur ve tarih arastirmasi asistanisin.

Gorevin, kullanicinin yukledigi fotografi ayrintili
incelemek ve asagidaki alanlari iceren GECERLI JSON
formatinda Turkce bir arastirma dosyasi hazirlamaktir.

Fotograf tek basina eserin kesin kimligini kanitlamaz.
Gozlem, yorum ve dogrulanmasi gereken iddialari ayir.
Bilinmeyen bilgileri uydurma.

JSON semasi:

{
  "eser_adi": "",
  "alternatif_adlar": "",
  "guven_duzeyi": "",
  "kimlik_gerekcesi": "",
  "genel_tanim": "",
  "gorunur_ozellikler": "",
  "uygarlik": "",
  "tarih_araligi": "",
  "tarih_araligi_gerekcesi": "",
  "cografi_baglam": "",
  "malzeme": "",
  "uretim_teknigi": "",
  "boyut_ve_olcek": "",
  "kullanim_amaci": "",
  "kullanim_amaci_gerekcesi": "",
  "sanatsal_ozellikler": "",
  "semboller_ve_motifler": "",
  "yazit_ve_isaretler": "",
  "dini_ve_kulturel_baglam": "",
  "donemin_siyasi_yapisi": "",
  "donemin_gunluk_yasami": "",
  "tarihsel_olaylarla_baglanti": "",
  "arkeolojik_baglam": "",
  "buluntu_yeri": "",
  "buluntu_yeri_guveni": "",
  "benzer_eserler": "",
  "diger_uygarliklarla_karsilastirma": "",
  "kulturel_etkilesim": "",
  "korunma_durumu": "",
  "restorasyon_ve_koruma": "",
  "tarihsel_onem": "",
  "yanlis_anlasilabilecek_noktalar": "",
  "bilinenler": "",
  "tahminler": "",
  "belirsizlikler": "",
  "uzmanin_incelemesi_gerekenler": "",
  "arastirma_sorulari": "",
  "kisa_ozet": ""
}

ARASTIRMA KURALLARI:

1. Tum alanlari mumkun oldugunca ayrintili doldur.
2. Turkce, acik ve anlasilir bir dil kullan.
3. Fotograf uzerinden dogrudan gorulebilen ayrintilari
   tarihsel yorumlardan ayri tut.
4. Eserin kimligini belirleyemiyorsan birden fazla
   olasilik sun ve nedenlerini acikla.
5. Kesin tarih, uretici, kazici, koleksiyon, muze,
   buluntu yeri veya arkeolojik kesif hikayesi uydurma.
6. Fotograf boyut vermiyorsa eserin gercek boyutunu
   kesin olarak bildigini iddia etme.
7. Yazi veya sembol okunmuyorsa bunu belirt.
8. Tarihsel baglam konusunda kesinlik derecesini acikla.
9. Benzer eserler bolumunde kesin olmayan benzerlikleri
   kesin es ozdesligi gibi sunma.
10. Canli internet arastirmasi yapmadiysan kaynaklari
    kontrol ettigini veya bilgileri dogruladigini soyleme.
11. Bilinmeyen alanlara acikca "Bilinmiyor" yaz.
12. JSON disinda metin, Markdown veya kod blogu yazma.
13. Alanlari tek kelimelik cevaplarla gecistirme;
    eldeki kanitlarin izin verdigi olcude aciklamalar yap.
"""

        prompt += (
            "\nArastirma derinligi: "
            + str(arastirma_turu)
        )

        if ek_bilgi and ek_bilgi.strip():
            prompt += (
                "\nKullanicinin ek bilgisi: "
                + ek_bilgi.strip()[:1500]
            )

        answer = gemini_istegi(
            image_base64,
            prompt
        )

        # JSON disinda kod blogu isaretleri gelirse temizle
        if answer.startswith("```"):
            lines = answer.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            answer = "\n".join(lines).strip()

        data = json.loads(answer)

        def field(key, default="Bilgi belirtilmedi."):
            value = data.get(key, default)

            if value is None or value == "":
                return default

            if isinstance(value, (dict, list)):
                return json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2
                )

            return str(value).strip()

        # Genel bakis
        genel = f"""# {field("eser_adi", "Eser tanimlanamadi")}

**Guven duzeyi:** {field("guven_duzeyi")}

## Kimlik tespiti ve gerekcesi

{field("kimlik_gerekcesi")}

## Alternatif adlar

{field("alternatif_adlar")}

## Genel tanim

{field("genel_tanim")}

## Fotograf uzerinde gorulen ozellikler

{field("gorunur_ozellikler")}

## Uygarlik ve tarih

**Uygarlik:** {field("uygarlik")}

**Tahmini tarih araligi:** {field("tarih_araligi")}

**Tarih tahmininin gerekcesi:** {field("tarih_araligi_gerekcesi")}

## Cografi baglam

{field("cografi_baglam")}

## Kisa ozet

{field("kisa_ozet")}
"""

        # Teknik ve sanatsal analiz
        teknik = f"""# Malzeme ve uretim

## Malzeme

{field("malzeme")}

## Uretim teknigi

{field("uretim_teknigi")}

## Boyut ve olcek

{field("boyut_ve_olcek")}

## Sanatsal ozellikler

{field("sanatsal_ozellikler")}

## Semboller ve motifler

{field("semboller_ve_motifler")}

## Yazitlar ve isaretler

{field("yazit_ve_isaretler")}

## Kullanim amaci

{field("kullanim_amaci")}

### Kullanim amacinin gerekcesi

{field("kullanim_amaci_gerekcesi")}
"""

        # Tarihsel baglam
        tarih = f"""# Tarihsel ve kulturel arka plan

## Dini ve kulturel baglam

{field("dini_ve_kulturel_baglam")}

## Donemin siyasi yapisi

{field("donemin_siyasi_yapisi")}

## Donemin gunluk yasami

{field("donemin_gunluk_yasami")}

## Tarihsel olaylarla baglanti

{field("tarihsel_olaylarla_baglanti")}

## Tarihsel onem

{field("tarihsel_onem")}

## Kulturler arasi etkilesim

{field("kulturel_etkilesim")}
"""

        # Arkeolojik analiz
        arkeoloji = f"""# Arkeolojik inceleme

## Arkeolojik baglam

{field("arkeolojik_baglam")}

## Buluntu yeri

{field("buluntu_yeri")}

**Buluntu yeri bilgisinin guveni:** {field("buluntu_yeri_guveni")}

## Benzer eserler

{field("benzer_eserler")}

## Diger uygarliklarla karsilastirma

{field("diger_uygarliklarla_karsilastirma")}

## Korunma durumu

{field("korunma_durumu")}

## Restorasyon ve koruma

{field("restorasyon_ve_koruma")}
"""

        # Elestirel degerlendirme
        elestiri = f"""# Kanitlar ve belirsizlikler

## Bilinenler

{field("bilinenler")}

## Tahminler

{field("tahminler")}

## Belirsizlikler

{field("belirsizlikler")}

## Yanlis anlasilabilecek noktalar

{field("yanlis_anlasilabilecek_noktalar")}

## Uzman incelemesi gerektiren konular

{field("uzmanin_incelemesi_gerekenler")}

## Ileri arastirma sorulari

{field("arastirma_sorulari")}
"""

        kaynaklar = """# Kaynak ve katalog arastirmasi

Bu uygulama bu analiz sirasinda bagimsiz internet
kaynaklarini otomatik olarak taramadi. Asagidaki
kurumlar ve kataloglar arastirmaya baslamak icindir.

- [UNESCO Dunya Mirasi Merkezi](https://whc.unesco.org/)
- [T.C. Kultur Portali](https://www.kulturportali.gov.tr/)
- [British Museum koleksiyon katalogu](https://www.britishmuseum.org/collection)
- [The Metropolitan Museum of Art koleksiyonu](https://www.metmuseum.org/art/collection)
- [Getty Research Institute](https://www.getty.edu/research/)
- [Europeana dijital kultur mirasi](https://www.europeana.eu/)

**Onemli:** Bu baglantilar, incelenen eserin bu
kataloglarda bulundugunu veya yapilan analizin
dogr
