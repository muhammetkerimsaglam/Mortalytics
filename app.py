import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Genişlik ve Başlık Ayarları
st.set_page_config(
    page_title="Mortalytics: Dinamik Kohort Simülasyonu & Aktüeryal Anüite Motoru (Demo)",
    page_icon="📊",
    layout="wide"
)

# ==============================================================================
# 1. TRH-2010 VERİ ÜRETİCİSİ
# ==============================================================================
@st.cache_data # Verinin her saniye yeniden hesaplanmaması için önbelleğe alıyoruz
def get_trh2010_data():
    """
    TRH-2010 yaşam tablosunun genel eğilimini (kadınların erkeklerden daha uzun
    yaşaması, yaşlılıkta hızlanan ölüm oranları vb.) yansıtan SENTETİK/YAKLAŞIK
    bir yaşam tablosu üretir.

    ÖNEMLİ: Bu fonksiyon TSB/SBM tarafından yayınlanan RESMİ TRH-2010 tablosunu
    kullanmaz. lx değerleri parametrik bir güç fonksiyonuyla üretilmiştir ve
    gerçek qx/lx değerlerinden sapabilir. Gerçek aktüeryal/hukuki hesaplamalar
    (tazminat, rezerv, prim vb.) için resmi TRH-2010 tablosu kullanılmalıdır.
    Bu araç yalnızca eğitim/demo amaçlıdır.

    Başlangıç kohortu (l0), her iki cinsiyet için de 100.000 kişi olarak kabul edilmiştir.
    """
    ages = np.arange(0, 101)
    lx_m = []
    lx_f = []
    l0 = 100000.0

    for x in ages:
        # Erkekler için TRH-2010 eğilimini yaklaşık yansıtan sentetik lx eğrisi (gerçek tablo değil)
        val_m = l0 * (1 - (x / 105) ** 4.2) if x < 100 else l0 * 0.005
        # Kadınlar için TRH-2010 eğilimini yaklaşık yansıtan sentetik lx eğrisi (kadınların beklenen ömrü daha uzun varsayılmıştır)
        val_f = l0 * (1 - (x / 108) ** 4.8) if x < 100 else l0 * 0.008

        # Bebeklik dönemi (0-5 yaş arası) hafif ölüm oranı düzeltmesi
        if x > 0:
            val_m *= 0.985
            val_f *= 0.988

        lx_m.append(max(0.0, val_m))
        lx_f.append(max(0.0, val_f))

    df = pd.DataFrame({
        'Age': ages,
        'lx_male': np.round(lx_m),
        'lx_female': np.round(lx_f)
    })

    # Ölüm olasılıklarının hesaplanması: qx = (lx - lx+1) / lx
    df['qx_male'] = (df['lx_male'] - df['lx_male'].shift(-1)) / df['lx_male']
    df['qx_female'] = (df['lx_female'] - df['lx_female'].shift(-1)) / df['lx_female']
    
    # Limit yaşta (omega = 100) herkesin vefat edeceği varsayılır (qx = 1.0)
    df.loc[df['Age'] == 100, 'qx_male'] = 1.0
    df.loc[df['Age'] == 100, 'qx_female'] = 1.0
    
    df.fillna(0, inplace=True)
    return df

# ==============================================================================
# 2. AKTÜERYAL HESAPLAMA MOTORU (KOMÜTASYON VE ANÜİTELER)
# ==============================================================================
class ActuarialEngine:
    def __init__(self, mortality_df: pd.DataFrame, interest_rate: float):
        """
        Komütasyon fonksiyonlarını ve anüiteleri hesaplayan aktüeryal motor.
        
        :param mortality_df: Yaşam tablosu verilerini içeren veri çerçevesi
        :param interest_rate: Teknik faiz oranı (örneğin %9 için 0.09)
        """
        self.df = mortality_df.copy()
        self.i = interest_rate
        self.v = 1 / (1 + self.i)  # İskonto faktörü

    def calculate_commutation_functions(self, gender: str = "male"):
        """
        Seçilen cinsiyete göre Dx ve Nx komütasyon değerlerini hesaplar.
        """
        lx_col = "lx_male" if gender == "male" else "lx_female"
        
        # Dx = v^x * lx
        self.df["Dx"] = (self.v ** self.df["Age"]) * self.df[lx_col]
        
        # Nx = x yaşından limit yaşa kadar olan Dx'lerin kümülatif toplamı
        self.df["Nx"] = self.df["Dx"].iloc[::-1].cumsum().iloc[::-1]
        return self.df

    def calculate_single_premium_annuity(self, age: int, gender: str = "male", annuity_type: str = "due"):
        """
        Ömür boyu anüite (tek primli emeklilik maaşı) değerini hesaplar.
        
        :param age: Bireyin yaşı (x)
        :param gender: 'male' (erkek) veya 'female' (kadın)
        :param annuity_type: 'due' (Dönem Başı) veya 'immediate' (Dönem Sonu)
        """
        df_comm = self.calculate_commutation_functions(gender)
        row = df_comm[df_comm["Age"] == age]
        if row.empty:
            return 0.0

        Dx = row["Dx"].values[0]
        Nx = row["Nx"].values[0]

        if Dx == 0:
            return 0.0

        if annuity_type == "due":
            # Dönem Başı Ödemeli Anüite: äx = Nx / Dx
            return Nx / Dx
        elif annuity_type == "immediate":
            # Dönem Sonu Ödemeli Anüite: ax = N_{x+1} / Dx
            next_row = df_comm[df_comm["Age"] == (age + 1)]
            if next_row.empty:
                return 0.0
            Nx_plus_1 = next_row["Nx"].values[0]
            return Nx_plus_1 / Dx

# ==============================================================================
# 3. MONTE CARLO KOHORT SİMÜLATÖRÜ
# ==============================================================================
class CohortSimulator:
    def __init__(self, mortality_df: pd.DataFrame):
        """
        Bireysel bazda yaşam ve ölüm süreçlerini simüle eden sınıf.
        """
        self.df = mortality_df

    def run_simulation(self, start_age: int, gender: str, cohort_size: int = 10000):
        """
        Her bir birey için yaşam/ölüm durumunu yıl yıl simüle eder.
        
        :param start_age: Simülasyonun başlayacağı yaş (emeklilik yaşı)
        :param gender: 'male' (erkek) veya 'female' (kadın)
        :param cohort_size: Başlangıçtaki toplam simüle edilecek kişi sayısı
        """
        # Sabit seed: aynı parametrelerle her çalıştırmada aynı (tekrarlanabilir) sonuç üretir
        np.random.seed(42)

        qx_col = 'qx_male' if gender == 'male' else 'qx_female'
        mortality_rates = self.df[self.df['Age'] >= start_age][['Age', qx_col]].copy()
        mortality_rates.rename(columns={qx_col: 'qx'}, inplace=True)
        
        sim_ages = mortality_rates['Age'].values
        num_years = len(sim_ages)
        
        # Başlangıçta tüm bireyler hayattadır (1: Hayatta, 0: Vefat Etmiş)
        status = np.ones((cohort_size, num_years))
        
        for t in range(1, num_years):
            # Bir önceki yıl hayatta olan bireylerin indekslerini bulalım
            still_alive_indices = np.where(status[:, t-1] == 1)[0]
            
            # O yaştaki ölüm olasılığı
            qx_current = mortality_rates.iloc[t-1]['qx']
            
            # Rastgele olasılık zarları atıyoruz (0 ile 1 arasında)
            random_draws = np.random.rand(len(still_alive_indices))
            
            # Eğer atılan zar ölüm olasılığından küçükse birey vefat eder
            deaths = random_draws < qx_current
            
            # Durum tablosunu güncelleyelim
            status[:, t] = status[:, t-1]
            status[still_alive_indices[deaths], t] = 0

        # Her yıl için hayatta kalan toplam kişi sayısı
        survivors_per_year = status.sum(axis=0)
        
        # Sonuçları düzenli bir veri çerçevesine dönüştürelim
        results = pd.DataFrame({
            'Year': np.arange(num_years),
            'Age': sim_ages,
            'Survivors': survivors_per_year,
            'Deaths_This_Year': np.diff(np.insert(cohort_size - survivors_per_year, 0, 0))
        })
        
        return results

@st.cache_data  # Sadece age/gender/cohort_size değiştiğinde yeniden hesaplanır
def run_cached_simulation(mortality_df: pd.DataFrame, start_age: int, gender: str, cohort_size: int):
    """
    CohortSimulator.run_simulation() için cache'lenmiş sarmalayıcı.
    Streamlit her widget etkileşiminde scripti baştan çalıştırdığından,
    bu cache olmadan simülasyon alakasız bir parametre (örn. yıllık ödeme
    tutarı) değiştiğinde bile gereksiz yere yeniden koşardı.
    """
    simulator = CohortSimulator(mortality_df)
    return simulator.run_simulation(start_age, gender, cohort_size)


# ==============================================================================
# 4. STREAMLIT ARAYÜZÜ (WEB TASARIMI)
# ==============================================================================

# Başlık Kısmı
st.title("📊 Mortalytics")
st.subheader("TRH-2010 Esintili Dinamik Kohort Simülasyonu & Aktüeryal Anüite Motoru")
st.markdown("Bu interaktif panel, bireysel emeklilik ve hayat sigortacılığı hesaplamalarında kullanılan komütasyon fonksiyonlarını hesaplar ve eşzamanlı olarak Monte Carlo simülasyonu ile kohort riskini canlandırır.")

st.warning(
    "**Bu bir demo/eğitim projesidir.** Kullanılan yaşam tablosu, TSB/SBM tarafından "
    "yayınlanan **resmi TRH-2010 tablosu değildir**; TRH-2010'un genel eğilimini "
    "(kadın-erkek farkı, yaşa bağlı artan ölüm oranı) yansıtan **sentetik/yaklaşık bir "
    "modeldir**. Gerçek aktüeryal, sigortacılık veya hukuki (tazminat vb.) hesaplamalarda "
    "kullanılmamalıdır.",
    icon="⚠️"
)

st.divider()

# Yan Panel (Giriş Parametreleri)
st.sidebar.header("⚙️ Simülasyon Parametreleri")

gender_input = st.sidebar.selectbox("Cinsiyet", ["Erkek", "Kadın"], index=0)
gender = "male" if gender_input == "Erkek" else "female"

age = st.sidebar.slider("Giriş / Emeklilik Yaşı (x)", min_value=18, max_value=90, value=65, step=1)

interest_rate_pct = st.sidebar.slider("Teknik Faiz Oranı (%)", min_value=0.0, max_value=20.0, value=9.0, step=0.5)
interest_rate = interest_rate_pct / 100.0

cohort_size = st.sidebar.number_input("Başlangıç Kohort Sayısı (Kişi)", min_value=100, max_value=100000, value=10000, step=500)

annuity_pay = st.sidebar.number_input("Yıllık Ödeme Tutarı (TL)", min_value=1000, value=100000, step=5000)

annuity_type_input = st.sidebar.selectbox(
    "Anüite Ödeme Tipi", 
    ["Dönem Başı Ödemeli (Peşin - äx)", "Dönem Sonu Ödemeli (ax)"]
)
annuity_type = "due" if "Dönem Başı" in annuity_type_input else "immediate"

# Hesaplamaları ve Simülasyonu Tetikle
trh_data = get_trh2010_data()
engine = ActuarialEngine(trh_data, interest_rate)
annuity_val = engine.calculate_single_premium_annuity(age, gender, annuity_type)

sim_results = run_cached_simulation(trh_data, age, gender, cohort_size)

# Hesaplanan Değerler (Kart Tasarımları)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Aktüeryal Anüite Faktörü (ax / äx)",
        value=f"{annuity_val:.4f}"
    )
with col2:
    st.metric(
        label="Kişi Başına Gereken Rezerv (BAP)",
        value=f"{annuity_pay * annuity_val:,.2f} TL"
    )
with col3:
    st.metric(
        label="Portföy Toplam Rezerv Yükümlülüğü",
        value=f"{cohort_size * annuity_pay * annuity_val:,.2f} TL"
    )

st.divider()

# Plotly Grafiği
st.write("### 📈 Kohort Yaşam ve Ölüm Eğrisi (Dinamik)")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Hayatta Kalanlar Çizgisi
fig.add_trace(
    go.Scatter(
        x=sim_results["Age"],
        y=sim_results["Survivors"],
        name="Hayatta Kalanlar",
        line=dict(color="#2ca02c", width=3),
        mode="lines+markers",
        hovertemplate="<b>Yaş:</b> %{x}<br><b>Hayatta Kalan:</b> %{y:,.0f} kişi<extra></extra>"
    ),
    secondary_y=False,
)

# Vefat Edenler Barı
fig.add_trace(
    go.Bar(
        x=sim_results["Age"],
        y=sim_results["Deaths_This_Year"],
        name="O Yıl Ölenler",
        marker_color="rgba(214, 39, 40, 0.7)",
        hovertemplate="<b>Yaş:</b> %{x}<br><b>Vefat Eden:</b> %{y:,.0f} kişi<extra></extra>"
    ),
    secondary_y=True,
)

fig.update_layout(
    xaxis_title="Yaş (x)",
    legend=dict(x=0.01, y=0.99, bgcolor="rgba(255, 255, 255, 0.5)"),
    hovermode="x unified",
    template="plotly_white",
    height=500
)

fig.update_yaxes(title_text="Aktif Hayatta Kalan Birey Sayısı", secondary_y=False)
fig.update_yaxes(title_text="Yıllık Vefat Sayısı", secondary_y=True)

st.plotly_chart(fig, use_container_width=True)

# Veri Tablosu İndirme Seçeneği
st.write("### 📋 Simülasyon Veri Akışı Detayları")
st.dataframe(sim_results, use_container_width=True)