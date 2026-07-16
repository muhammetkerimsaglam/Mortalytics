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

---

## 🛠️ Kullanılan Teknolojiler

*   **Python 3.x**
*   **Streamlit** (Web arayüzü ve canlı dağıtım)
*   **Plotly** (İnteraktif ve çift eksenli grafikler)
*   **Pandas & NumPy** (Matematiksel motor ve veri manipülasyonu)

---

## 💻 Kurulum ve Yerelde Çalıştırma

Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları takip edebilirsiniz:

1.  **Depoyu klonlayın:**
    ```bash
    git clone [https://github.com/KULLANICI_ADINIZ/mortalytics.git](https://github.com/KULLANICI_ADINIZ/mortalytics.git)
    cd mortalytics
    ```

2.  **Gerekli kütüphaneleri yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Uygulamayı başlatın:**
    ```bash
    streamlit run app.py
    ```

---

## 📐 Aktüeryal Metot ve Varsayımlar

### Komütasyon Fonksiyonları
Uygulama, iskonto faktörü $v = \frac{1}{1+i}$ olmak üzere aşağıdaki formülleri kullanır:

*   **Yaşam Değeri ($D_x$):** 
    $$D_x = v^x \cdot l_x$$
*   **Kümülatif Yaşam Değeri ($N_x$):** 
    $$N_x = \sum_{t=0}^{\omega - x} D_{x+t}$$

### Anüite Değerleri
*   **Dönem Başı Ödemeli (Peşin - $\ddot{a}_x$):**
    $$\ddot{a}_x = \frac{N_x}{D_x}$$
*   **Dönem Sonu Ödemeli (Adi - $a_x$):**
    $$a_x = \frac{N_{x+1}}{D_x}$$

> **Model Sınırlaması Notu:** Grafiğin uç noktasında (100 yaş) görülen yığılma, TRH-2010 yaşam tablosunun limit yaşının ($\omega = 100$) kabul edilmesinden ve bu yaşta ölüm olasılığının ($q_{100} = 1.0$) olarak tanımlanmasından kaynaklanan doğal bir model sonucudur.

---

## 📧 İletişim ve Geri Bildirim

Proje hakkında sorularınız, iş birliği önerileriniz veya geri bildirimleriniz için benimle LinkedIn üzerinden iletişime geçebilirsiniz!
https://www.linkedin.com/in/muhammet-kerim-sa%C4%9Flam-69710625b/
*   **Geliştirici:** Muhammet Kerim Sağlam
