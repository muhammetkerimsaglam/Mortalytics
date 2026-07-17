# 📊 Mortalytics

**TRH-2010 Esintili Dinamik Kohort Simülasyonu & Aktüeryal Anüite Motoru**

🔗 **Canlı Demo:** [mortalytics-jzecyyzqtfzepuwnyzyhag.streamlit.app](https://mortalytics-jzecyyzqtfzepuwnyzyhag.streamlit.app/)

Mortalytics, bireysel emeklilik ve hayat sigortacılığında kullanılan aktüeryal
komütasyon fonksiyonlarını (Dx, Nx) hesaplayan, farklı anüite tiplerini
karşılaştıran ve Monte Carlo simülasyonuyla bir kohortun (yaş grubunun)
zaman içindeki yaşam/ölüm dağılımını görselleştiren interaktif bir
Streamlit uygulamasıdır.

---

## ⚠️ Önemli Not: Veri Kaynağı Hakkında

Bu proje **eğitim ve portfolyo amaçlı bir demodur**. Kullanılan yaşam
tablosu, Türkiye Sigorta Birliği (TSB) / Sigorta Bilgi ve Gözetim Merkezi
(SBM) tarafından yayınlanan **resmi TRH-2010 tablosu değildir**.

`math_engine.generate_trh2010_data()` fonksiyonu, TRH-2010'un genel
eğilimini (kadınların erkeklerden daha uzun yaşaması, yaşa bağlı artan
ölüm oranı gibi) yansıtan **parametrik/sentetik bir yaklaşıklama**
üretir. Gerçek qx/lx değerlerinden sapabilir.

**Bu nedenle: gerçek aktüeryal, sigortacılık veya hukuki (tazminat vb.)
hesaplamalarda kesinlikle kullanılmamalıdır.**

---

## ✨ Özellikler

- **Komütasyon fonksiyonları:** Dx = vˣ·lx ve Nx (kümülatif Dx toplamı) hesaplaması
- **6 farklı anüite tipi**, iki eksende seçilebilir:
  - **Anüite Şekli:** Ömür Boyu (Whole Life) · Ertelemeli (Deferred) · n Yıl Vadeli (Term)
  - **Ödeme Zamanlaması:** Dönem Başı (Peşin - äx) · Dönem Sonu (ax)
- **Monte Carlo kohort simülasyonu:** Binlerce bireyi yıl yıl simüle ederek
  hayatta kalan/vefat eden sayısını canlandırır (sabit seed ile tekrarlanabilir)
- **Dinamik rezerv hesaplama:** Kişi başına ve portföy toplamına göre
  gereken aktüeryal rezerv
- **İnteraktif Plotly grafiği:** Hayatta kalan sayısı ve yıllık vefat sayısı
  aynı grafikte, çift eksenli olarak gösterilir

---

## 🧮 Kullanılan Formüller

| Anüite Tipi | Formül |
|---|---|
| Ömür boyu, dönem başı (peşin) | äx = Nx / Dx |
| Ömür boyu, dönem sonu | ax = N₍x+1₎ / Dx |
| n yıl ertelemeli, dönem başı | ₙ\|äx = N₍x+n₎ / Dx |
| n yıl ertelemeli, dönem sonu | ₙ\|ax = N₍x+n+1₎ / Dx |
| n yıl vadeli, dönem başı | ₙäx = (Nx − N₍x+n₎) / Dx |
| n yıl vadeli, dönem sonu | ₙax = (N₍x+1₎ − N₍x+n+1₎) / Dx |

**Matematiksel doğrulama (invariant):** Herhangi bir n değeri için,
*n yıl vadeli anüite + n yıl ertelemeli anüite = ömür boyu anüite*
eşitliği her zaman sağlanır. Bu özellik `test_actuarial.py` içinde
otomatik olarak test edilir.

---

## 📁 Proje Yapısı

```
Mortalytics/
├── app.py                  # Streamlit arayüzü (giriş noktası)
├── math_engine.py           # ⭐ Tek gerçek kaynak: tüm hesaplama mantığı
├── actuarial_engine.py       # Geriye dönük uyumluluk için ince sarmalayıcı
├── trh2010_generator.py      # Geriye dönük uyumluluk için ince sarmalayıcı
├── main_test.py              # Notebook kökenli manuel inceleme/demo scripti
├── test_actuarial.py         # pytest test paketi (13 test)
├── requirements.txt          # Python bağımlılıkları
└── README.md
```

`math_engine.py`, projenin **tek gerçek kaynağıdır (single source of
truth)**. Streamlit'e bağımlı değildir, bu sayede hem `pytest` ile
kolayca test edilebilir hem de diğer tüm dosyalar (`app.py`,
`actuarial_engine.py`, `trh2010_generator.py`, `main_test.py`) buradan
import ederek her zaman birbiriyle tutarlı sonuç üretir. Bir hesaplama
mantığını değiştirmeniz gerektiğinde tek düzenlemeniz gereken dosya budur.

---

## 🚀 Kurulum ve Çalıştırma

```bash
git clone https://github.com/muhammetkerimsaglam/Mortalytics.git
cd Mortalytics
pip install -r requirements.txt
streamlit run app.py
```

### Testleri çalıştırmak için

```bash
pip install pytest
pytest test_actuarial.py -v
```

---

## 🛠️ Kullanılan Teknolojiler

- **Streamlit** — interaktif web arayüzü
- **NumPy / Pandas** — sayısal hesaplama ve veri işleme
- **Plotly** — interaktif görselleştirme
- **pytest** — birim testleri

---

## 🔭 Yol Haritası (Planlanan Geliştirmeler)

- [ ] Gerçek/resmi TRH-2010 verisiyle sentetik modelin karşılaştırmalı gösterimi
- [ ] Monte Carlo simülasyonu için çoklu-koşum dağılım/histogram grafiği (rezerv yeterliliği olasılığı)
- [ ] PDF rapor çıktısı (seçilen parametreler + sonuçlar)
- [ ] Joint-life (çoklu yaşam) anüite desteği

---
**Hazırlayan: MUHAMMET KERİM SAĞLAM**
## 📄 Lisans

Bu proje eğitim/portfolyo amaçlı hazırlanmıştır.
