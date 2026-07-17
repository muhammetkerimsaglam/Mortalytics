# 📊 Mortalytics: TRH-2010 Esintili Dinamik Kohort Simülasyonu & Aktüeryal Anüite Motoru

Mortalytics, bireysel emeklilik ve hayat sigortacılığı hesaplamalarında kullanılan aktüeryal komütasyon fonksiyonlarını dinamik olarak hesaplayan ve Monte Carlo simülasyonu ile bir kohortun (grubun) maruz kaldığı mortalite riskini yaşayan bir grafikle görselleştiren interaktif bir web uygulamasıdır.

Bu proje; deterministik aktüeryal hesaplamaların gücünü, stokastik (rastsal) simülasyon dünyası ve modern veri analitiği araçlarıyla birleştirmek amacıyla geliştirilmiştir.

---

## 🚀 Öne Çıkan Özellikler

*   **TRH-2010 Esintili Yaşam Tablosu Entegrasyonu:** Türkiye'de hayat ve emeklilik branşlarında standart kabul edilen TRH-2010 mortalite verilerini temel alır.
*   **Dinamik Aktüeryal Motor:** Kullanıcının seçtiği teknik faiz oranına ($i$) ve cinsiyete göre $D_x$ ve $N_x$ komütasyon fonksiyonlarını anlık olarak hesaplar.
*   **Dönem Başı & Dönem Sonu Anüite:** Tek primli ömür boyu anüite faktörlerini (Peşin $\ddot{a}_x$ ve Adi $a_x$) saniyeler içinde çıkarır.
*   **Monte Carlo Kohort Simülasyonu:** Geleneksel hesaplamaların ötesine geçerek, belirlenen büyüklükteki bir emekli grubunun her yıl maruz kaldığı ölüm olasılıklarına ($q_x$) göre "zar atarak" yıllar içindeki erimesini simüle eder.
*   **Bilanço ve Karşılık Analizi:** Kişi başına gereken rezerv (BAP) ile tüm grubun şirkete getireceği **Portföy Toplam Rezerv Yükümlülüğünü** hesaplar.
*   **Gelişmiş Görselleştirme:** Plotly alt yapısıyla hazırlanan çift eksenli grafik sayesinde aktif hayatta kalanlar ile yıllık vefat sayıları dinamik olarak izlenebilir.
### 📊 Aktüeryal Anüite Modelleme Çeşitleri
Motor, bireysel emeklilik ve hayat sigortacılığı matematiksel altyapısına uygun olarak üç temel anüite tipini dinamik komütasyon fonksiyonları üzerinden hesaplar:
*   **Dönem Başı Ödemeli Peşin Anüite ($\ddot{a}_x$):** Ödemelerin her dönemin başında yapıldığı standart ömür boyu maaş modeli.
*   **Dönem Sonu Ödemeli Adi Anüite ($a_x$):** Ödemelerin dönem sonlarında gerçekleştiği aktüeryal model.
*   **Ertelemeli Dönem Başı Ödemeli Anüite ($_n|\ddot{a}_x$):** Belirlenen bir erteleme süresi ($postponement/deferral$) boyunca rezerv yükümlülüğü biriktiren ve süre sonunda aktif hale gelen gelişmiş aktüeryal model.
---

## 🛠️ Kullanılan Teknolojiler

*   **Python**
*   **Streamlit** (Web arayüzü ve canlı dağıtım)
*   **Plotly** (İnteraktif ve çift eksenli grafikler)
*   **Pandas & NumPy** (Matematiksel motor ve veri manipülasyonu)

---
## 📝 Metodoloji ve Aktüeryal Altyapı

Bu proje, bireysel emeklilik ve hayat sigortacılığı ürünlerinin fiyatlandırılmasında kullanılan deterministik ve stokastik modelleme dinamiklerini bir arada sunmaktadır.

### 1. Aktüeryal Varsayımlar ve Yaşam Tablosu (TRH-2010)
*   **Mortalite Varsayımı:** Modelde, Türkiye sigortacılık pazarında yasal olarak da referans kabul edilen **TRH-2010 Kadın/Erkek Yaşam Tablosu**'nun genel eğilimleri baz alınmıştır. Yaşa bağlı artan ölüm olasılıkları ($q_x$) ve cinsiyetler arası mortalite farkları bu tabloya göre simüle edilmektedir.
*   **Teknik Faiz Oranı ($i$):** Gelecekteki nakit akışlarının bugünkü değere indirgenmesinde kullanılan deterministik iskonto oranıdır (Arayüzden dinamik olarak değiştirilebilir).
*   **İskonto Faktörü ($v$):** Finansal matematiğin temel indirgeme katsayısı olup şu şekilde hesaplanır:
    $$v = \frac{1}{1 + i}$$

### 2. Matematiksel Model ve Komütasyon Fonksiyonları
Hesaplamaların optimize edilmesi ve deterministik anüite değerlerinin bulunması için aktüeryal matematikteki standart komütasyon fonksiyonları kullanılmıştır:

*   **Yaşayan Kişi Sayısı ($l_x$):** İlgili yaşta hayatta kalan temsilî kohort büyüklüğü.
*   **D_x Fonksiyonu:** İskonto edilmiş hayatta kalan kişi sayısı:
    $$D_x = v^x \cdot l_x$$
*   **N_x Fonksiyonu:** $x$ yaşından limit yaşa ($\omega$) kadar olan tüm $D_x$ değerlerinin kümülatif toplamı:
    $$N_x = \sum_{t=0}^{\omega - x} D_{x+t}$$

### 3. Kullanılan Anüite Formülleri

Sistem, komütasyon fonksiyonlarını kullanarak aşağıdaki üç temel aktüeryal anüite değerini ($PVP$ - Muhtemel Bugünkü Değer) hesaplar:

*   **Dönem Başı Ödemeli Peşin Anüite ($\ddot{a}_x$):**
    $$\ddot{a}_x = \frac{N_x}{D_x}$$
*   **Dönem Sonu Ödemeli Adi Anüite ($a_x$):**
    $$a_x = \frac{N_{x+1}}{D_x}$$
*   *   **n-Yıl Ertelemeli Peşin Anüite ($_n|\ddot{a}_x$):** $_n|\ddot{a}_x = \frac{N_{x+n}}{D_x}$

### 4. Kohort Risk Simülasyonu (Monte Carlo)
Deterministik formüllerin aksine, kohortun gelecekteki yaşam seyrindeki sapmaları (aktüeryal risk) ölçmek için **Monte Carlo Simülasyonu** entegre edilmiştir. Her bir birey için $x$ yaşından itibaren her yıl için $[0, 1]$ aralığında düzgün dağılımdan rastgele sayılar üretilir. Eğer üretilen sayı o yaştaki ölüm olasılığından ($q_x$) küçükse bireyin vefat ettiği varsayılır. Bu işlem tüm kohort için tekrarlanarak büyük sayılar kanunu (Law of Large Numbers) görselleştirilir.

### 5. Referanslar
*   Bowers, N. L., Gerber, H. U., Hickman, J. C., Jones, D. A., & Nesbitt, C. J. (1997). *Actuarial Mathematics* (2nd ed.). Society of Actuaries.
*   Dickson, D. C., Hardy, M. R., & Waters, H. R. (2019). *Actuarial Mathematics for Life Contingent Risks*. Cambridge University Press.
*   Hazine Müsteşarlığı / Sigortacılık Bilgi ve Gözetim Merkezi (SBM) TRH-2010 Mortalite Tablosu Kılavuzları.


> **Model Sınırlaması Notu:** Grafiğin uç noktasında (100 yaş) görülen yığılma, TRH-2010 yaşam tablosunun limit yaşının ($\omega = 100$) kabul edilmesinden ve bu yaşta ölüm olasılığının ($q_{100} = 1.0$) olarak tanımlanmasından kaynaklanan doğal bir model sonucudur.

---


## 📧 İletişim ve Geri Bildirim

Proje hakkında sorularınız, iş birliği önerileriniz veya geri bildirimleriniz için benimle LinkedIn üzerinden iletişime geçebilirsiniz!
https://www.linkedin.com/in/muhammet-kerim-sa%C4%9Flam-69710625b/
*   **Geliştirici:** Muhammet Kerim Sağlam
