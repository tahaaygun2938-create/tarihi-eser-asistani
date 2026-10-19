
import os
import io
import json
import time
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
        API_KEY = getpass.getpass(
            "Gemini API anahtarını gir: "
        ).strip()
    except Exception:
        API_KEY = ""

# ==================================================
# MODEL KONTROLÜ
# ==================================================

def model_kontrol():
    if not API_KEY:
        print(
            "UYARI: GEMINI_API_KEY bulunamadı. "
            "Uygulama açılabilir ancak analiz yapılamaz."
        )
        return

    try:
        r = requests.get(
            f"{API_URL}/models",
            headers={"x-goog-api-key": API_KEY},
            timeout=20
        )

        if r.status_code != 200:
            print("Model kontrolü uyarısı:", r.status_code)
            return

        modeller = r.json().get("models", [])

        bulunan = next(
            (
                m for m in modeller
                if m.get("name", "").removeprefix("models/")
                == MODEL_ID
            ),
            None
        )

        if bulunan is None:
            print(
                f"UYARI: {MODEL_ID} listede görünmüyor. "
                "API anahtarının erişimini ve model adını kontrol et."
            )
        elif "generateContent" not in bulunan.get(
            "supportedGenerationMethods", []
        ):
            print(
                f"UYARI: {MODEL_ID} generateContent desteklemiyor."
            )

    except requests.RequestException as e:
        print("Model kontrolü yapılamadı:", e)


model_kontrol()

# ==================================================
# GEMINI İSTEĞİ
# ==================================================

def gemini_istegi(govde):
    if not API_KEY:
        raise RuntimeError(
            "API anahtarı bulunamadı. "
            "Render Environment bölümüne GEMINI_API_KEY ekle."
        )

    url = f"{API_URL}/models/{MODEL_ID}:generateContent"

    for deneme in range(2):
        try:
            r = requests.post(
                url,
                headers={
                    "x-goog-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                json=govde,
                timeout=120
            )
        except requests.RequestException as e:
            if deneme == 0:
                time.sleep(2)
                continue
            raise RuntimeError(f"Bağlantı hatası: {e}")

        if r.status_code == 200:
            return r.json()

        try:
            detay = r.json().get("error", {}).get(
                "message", r.text[:500]
            )
        except Exception:
            detay = r.text[:500]

        if r.status_code == 429:
            raise RuntimeError(
                "Gemini API kullanım kotası dolmuş olabilir (429).\n\n"
                + detay
            )

        if r.status_code in (401, 403):
            raise RuntimeError(
                "API anahtarı geçersiz veya erişim izni yok.\n\n"
                + detay
            )

        if r.status_code in (500, 502, 503, 504) and deneme == 0:
            time.sleep(2)
            continue

        raise RuntimeError(
            f"Gemini HTTP {r.status_code}: {detay}"
        )

    raise RuntimeError("İstek tamamlanamadı.")


# ==================================================
# JSON YANITINI OKU
# ==================================================

def json_oku(metin):
    metin = metin.strip()

    if metin.startswith("```"):
        satirlar = metin.splitlines()

        if satirlar and satirlar[0].startswith("```"):
            satirlar = satirlar[1:]

        if satirlar and satirlar[-1].strip() == "```":
            satirlar = satirlar[:-1]

        metin = "\n".join(satirlar).strip()

    baslangic = metin.find("{")
    bitis = metin.rfind("}")

    if baslangic == -1 or bitis == -1:
        raise ValueError("Geçerli bir JSON yanıtı bulunamadı.")

    return json.loads(metin[baslangic:bitis + 1])


# ==================================================
# AYRINTILI ESER ANALİZİ
# ==================================================

def eser_ara(fotograf, ek_bilgi):
    if fotograf is None:
        return ("Önce bir fotoğraf yükle.", "", "", "", "", "", "", "")

    try:
        with Image.open(fotograf) as im:
            im = im.convert("RGB")
            im.thumbnail((1400, 1400))

            tampon = io.BytesIO()
            im.save(tampon, format="JPEG", quality=88)

            foto_data = base64.b64encode(
                tampon.getvalue()
            ).decode("utf-8")

        prompt = """
Sen arkeoloji, tarih, sanat tarihi, epigrafi,
nümizmatik ve kültürel miras alanlarında çalışan
dikkatli bir araştırma asistanısın.

Görevin, yüklenen fotoğraftaki nesneyi mümkün olduğunca
ayrıntılı incelemek ve Türkçe bir analiz hazırlamaktır.

ÇOK ÖNEMLİ KURALLAR:
1. Fotoğrafta doğrudan görülen özellikleri, tarihsel
   yorumlardan ayrı değerlendir.
2. Eserin kimliği kesin değilse alternatif olasılıkları belirt.
3. Görselde olmayan ayrıntıları uydurma.
4. Tarih, medeniyet, üretim yeri ve kullanım amacı hakkındaki
   tahminlerini gerekçeleriyle açıkla.
5. Malzeme, yazıt, sembol veya hasar fotoğraftan anlaşılamıyorsa
   bunu açıkça belirt.
6. Bir nesnenin yalnızca görünüşüne bakarak orijinal olduğunu
   veya sahte olduğunu kesin biçimde söyleme.
7. Görseldeki yazılar okunabiliyorsa aktar; okunamıyorsa metin
   uydurma.
8. Benzer eserlerden söz ederken kesin eşleşme ile genel
   benzerliği birbirinden ayır.
9. Fotoğrafta görülen bir nesnenin gerçek müze kaydını,
   envanter numarasını, kazı yerini veya yayınını bilmiyorsan
   bunları uydurma.
10. Gerçek zamanlı internet araştırması yapmadığını unutma.
    Bir kaynağın kontrol edildiğini veya eserin o kaynakta
    bulunduğunu iddia etme.
11. Her alanı mümkün olduğunca bilgilendirici yaz.
    Ancak ayrıntı üretmek için gerçeğe aykırı bilgi ekleme.
12. Türkçe, anlaşılır ve düzenli yaz.

Yalnızca aşağıdaki alanları içeren geçerli JSON döndür.
JSON dışında açıklama yazma.

{
  "eser_adi": "Eserin olası adı veya tanımı",
  "guven": "Düşük, orta veya yüksek; gerekçesi",
  "genel_bakis": "Eserin ayrıntılı genel tanıtımı",
  "gorunur_ozellikler": "Fotoğrafta doğrudan görülebilen ayrıntılar",
  "malzeme": "Olası malzeme ve bu tahminin dayanakları",
  "bicim": "Form, boyut izlenimi, parçalar ve fiziksel yapı",
  "yapim_teknigi": "Muhtemel üretim ve işçilik tekniği",
  "donem": "Olası tarih veya dönem ve gerekçesi",
  "medeniyet": "Olası medeniyet veya kültürel çevre",
  "cografi_koken": "Olası coğrafi köken ve belirsizlikler",
  "tarihce": "Dönemin tarihsel koşulları ve eserle ilişkisi",
  "sanat_ozellikleri": "Sanat üslubu, tasarım, motifler ve bezemeler",
  "semboller": "Görülen semboller ve olası anlamları",
  "yazi": "Yazıt, alfabe, dil ve okunabilen ifadeler",
  "kullanim_amaci": "Muhtemel kullanım amacı ve gerekçesi",
  "toplumsal_yasam": "Günlük yaşam, gelenekler ve toplumla ilişkisi",
  "dini_baglam": "Varsa dinî, ritüel veya törensel bağlantı",
  "siyasi_baglam": "Varsa yönetim, hükümdarlık veya askerî bağlantı",
  "ekonomik_baglam": "Ticaret, para, üretim veya ekonomik hayatla ilişkisi",
  "arkeolojik_deger": "Arkeolojik açıdan önemi ve olası araştırma soruları",
  "benzer_eserler": "Karşılaştırılabilecek eser türleri ve benzerlik gerekçeleri",
  "buluntu_yeri": "Biliniyorsa buluntu yeri; fotoğraftan bilinmiyorsa bunu belirt",
  "korunma_durumu": "Fotoğraftan görülebilen aşınma, kırık veya yüzey durumu",
  "orijinallik": "Fotoğraftan orijinalliğin neden kesinleştirilemeyeceği",
  "alternatifler": "Diğer olası kimlikler ve bunların gerekçeleri",
  "belirsizlikler": "Eksik kanıtlar ve yanlış tanımlama riskleri",
  "dogrulama": "Kesin kimlik için gereken ek fotoğraf, ölçüm, yazıt veya belge",
  "arastirma_yollari": "Eser hakkında araştırma yapılabilecek kurum ve katalog türleri"
}

Eserin belirli bir tarihsel kimliği olduğundan emin değilsen
önce nesneyi tanımla, ardından olasılıkları gerekçelendir.
"""

        ek_bilgi = (ek_bilgi or "").strip()

        if not ek_bilgi:
            ek_bilgi = "Kullanıcı ek bilgi vermedi."

        govde = {
            "contents": [{
                "parts": [
                    {
                        "text": (
                            prompt
                            + "\n\nKullanıcının verdiği ek bilgi:\n"
                            + ek_bilgi
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": foto_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "maxOutputTokens": 5000
            }
        }

        sonuc = gemini_istegi(govde)
        adaylar = sonuc.get("candidates", [])

        if not adaylar:
            return (
                "Model analiz üretemedi.",
                "", "", "", "", "", "",
                "Model yanıt vermedi. Tekrar deneyebilirsin."
            )

        parcalar = adaylar[0].get(
            "content", {}
        ).get("parts", [])

        metin = "\n".join(
            p.get("text", "")
            for p in parcalar
            if p.get("text")
        ).strip()

        if not metin:
            raise RuntimeError(
                "Model boş yanıt verdi. Yanıt uzunluğu sınırına "
                "ulaşılmış olabilir; tekrar dene."
            )

        bilgi = json_oku(metin)

        def alan(ad, varsayilan="Bu konuda yeterli bilgi belirlenemedi."):
            deger = bilgi.get(ad, varsayilan)

            if deger is None:
                return varsayilan

            if isinstance(deger, (dict, list)):
                return json.dumps(
                    deger,
                    ensure_ascii=False,
                    indent=2
                )

            return str(deger).strip()

        def bolum(baslik, anahtar):
            return f"### {baslik}\n\n{alan(anahtar)}"

        # GENEL BAKIŞ

        genel = (
            f"# 🏛️ {alan('eser_adi', 'Tanımlanamayan nesne')}\n\n"
            f"**Tahmini güven düzeyi:** {alan('guven')}\n\n"
            f"## Genel tanıtım\n\n{alan('genel_bakis')}\n\n"
            f"## Fotoğrafta görülen özellikler\n\n"
            f"{alan('gorunur_ozellikler')}\n\n"
            f"## Malzeme ve fiziksel yapı\n\n"
            f"{alan('malzeme')}\n\n{alan('bicim')}\n\n"
            f"## Üretim tekniği\n\n{alan('yapim_teknigi')}"
        )

        # TARİH VE MEDENİYET

        tarih = "\n\n".join([
            bolum("Olası dönem", "donem"),
            bolum("Medeniyet ve kültürel çevre", "medeniyet"),
            bolum("Coğrafi köken", "cografi_koken"),
            bolum("Tarihsel bağlam", "tarihce"),
            bolum("Buluntu yeri", "buluntu_yeri")
        ])

        # SANAT VE KULLANIM

        sanat = "\n\n".join([
            bolum("Sanat özellikleri", "sanat_ozellikleri"),
            bolum("Semboller ve motifler", "semboller"),
            bolum("Yazıt ve dil", "yazi"),
            bolum("Kullanım amacı", "kullanim_amaci"),
            bolum("Toplumsal yaşam", "toplumsal_yasam")
        ])

        # TARİHSEL BAĞLAM

        baglam = "\n\n".join([
            bolum("Dinî ve törensel bağlam", "dini_baglam"),
            bolum("Siyasi ve askerî bağlam", "siyasi_baglam"),
            bolum("Ekonomik bağlam", "ekonomik_baglam"),
            bolum("Arkeolojik değer", "arkeolojik_deger"),
            bolum("Benzer eserler", "benzer_eserler")
        ])

        # ELEŞTİREL İNCELEME

        inceleme = "\n\n".join([
            bolum("Korunma durumu", "korunma_durumu"),
            bolum("Orijinallik değerlendirmesi", "orijinallik"),
            bolum("Alternatif tanımlamalar", "alternatifler"),
            bolum("Belirsizlikler", "belirsizlikler"),
            bolum("Nasıl doğrulanabilir?", "dogrulama")
        ])

        # KAYNAK ARAŞTIRMASI

        kaynak = (
            "## 📚 Araştırma yolları\n\n"
            + alan("arastirma_yollari")
            + """

### Başvurulabilecek kataloglar

- [UNESCO Dünya Mirası Merkezi](https://whc.unesco.org/)
- [T.C. Kültür Portalı](https://www.kulturportali.gov.tr/)
- [The British Museum Collection](https://www.britishmuseum.org/collection)
- [The Metropolitan Museum of Art Collection](https://www.metmuseum.org/art/collection)

**Önemli:** Bu bağlantılar araştırmaya başlamak içindir.
Bu analiz sırasında söz konusu kataloglarda canlı arama
yapılmadı ve eserin bu kataloglarda bulunduğu doğrulanmadı.
"""
        )

        durum = (
            "Analiz tamamlandı. Sonuçlar fotoğrafa dayalı yapay zekâ "
            "değerlendirmesidir. Kesin kimlik, tarih ve köken için "
            "müze kataloğu veya uzman incelemesi gerekebilir."
        )

        return (
            genel,
            tarih,
            sanat,
            baglam,
            inceleme,
            kaynak,
            durum
        )

    except Exception as e:
        hata = str(e)
        print("ESER ANALİZ HATASI:", repr(e))

        return (
            f"## ⚠️ Analiz tamamlanamadı\n\n{hata}",
            "", "", "", "", "",
            "Hata ayrıntısı yukarıda gösterildi."
        )


# ==================================================
# TASARIM - KOYU VE ALTIN TEMASI KORUNDU
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
    background: linear-gradient(90deg, transparent, #e5c47a, transparent);
}

#turk-bayragi {
    position: absolute;
    top: 18px;
    right: 20px;
    width: 65px;
    border-radius: 3px;
    box-shadow: 0 2px 10px rgba(0,0,0,.4);
}

button.primary {
    background: linear-gradient(90deg, #a77b32, #e2c477) !important;
    color: #17130b !important;
    font-weight: bold !important;
    border: none !important;
}

.panel {
    border: 1px solid #4a4437;
    border-radius: 14px;
    padding: 12px;
}

@media (max-width: 600px) {
    #turk-bayragi {
        width: 42px;
        top: 10px;
        right: 10px;
    }
}
"""


# ==================================================
# GRADIO ARAYÜZÜ
# ==================================================

with gr.Blocks(
    title="Tarihî Eser Asistanı",
    theme=gr.themes.Soft(),
    css=css
) as uygulama:

    gr.HTML("""
    <div id="hero">
      <img id="turk-bayragi"
           src="https://flagcdn.com/w160/tr.png"
           alt="Türk Bayrağı">
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
        "Bir eser fotoğrafı yükle ve araştırmayı başlat."
    )

    with gr.Group(elem_classes=["panel"]):
        fotograf_girdisi = gr.Image(
            label="Eser fotoğrafı",
            type="filepath",
            height=320
        )

        ek_bilgi_girdisi = gr.Textbox(
            label="Eser hakkında bildiklerin (isteğe bağlı)",
            placeholder="Bulunduğu yer, tahmini dönem, üzerindeki yazılar...",
            lines=2
        )

        arastir_butonu = gr.Button(
            "✦ ESERİ İNCELE",
            variant="primary",
            size="lg"
        )

    gr.Markdown("## Araştırma dosyası")

    with gr.Tabs():
        with gr.Tab("🏛️ Genel Bakış"):
            genel_cikti = gr.Markdown(
                "Eser tanıtımı burada görünecek."
            )

        with gr.Tab("📜 Tarih ve Medeniyet"):
            tarihce_cikti = gr.Markdown(
                "Tarihsel bilgiler burada görünecek."
            )

        with gr.Tab("🎨 Sanat ve Kullanım"):
            sanat_cikti = gr.Markdown(
                "Sanatsal özellikler burada görünecek."
            )

        with gr.Tab("🌍 Tarihsel Bağlam"):
            baglam_cikti = gr.Markdown(
                "Toplumsal ve tarihsel bilgiler burada görünecek."
            )

        with gr.Tab("🔎 Eleştirel İnceleme"):
            inceleme_cikti = gr.Markdown(
                "Belirsizlikler ve doğrulama yolları burada görünecek."
            )

        with gr.Tab("📚 Kaynaklar"):
            kaynak_cikti = gr.Markdown(
                "Araştırma kaynakları burada görünecek."
            )

    durum_cikti = gr.Markdown("Hazır.")

    arastir_butonu.click(
        fn=eser_ara,
        inputs=[
            fotograf_girdisi,
            ek_bilgi_girdisi
        ],
        outputs=[
            genel_cikti,
            tarihce_cikti,
            sanat_cikti,
            baglam_cikti,
            inceleme_cikti,
            kaynak_cikti,
            durum_cikti
        ],
        show_progress="full"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    uygulama.queue().launch(
        server_name="0.0.0.0",
        server_port=port
    )
