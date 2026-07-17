import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from math_engine import generate_trh2010_data, ActuarialEngine, CohortSimulator

# Sayfa Genişlik ve Başlık Ayarları
st.set_page_config(
    page_title="Mortalytics: Dinamik Kohort Simülasyonu & Aktüeryal Anüite Motoru (Demo)",
    page_icon="📊",
    layout="wide"
)


# ==============================================================================
# STREAMLIT CACHE SARMALAYICILARI
# (math_engine.py Streamlit'e bağımlı olmadığı için önbellekleme burada yapılır)
# ==============================================================================
@st.cache_data  # Verinin her etkileşimde yeniden hesaplanmaması için önbelleğe alıyoruz
def get_trh2010_data():
    return generate_trh2010_data()


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
# STREAMLIT ARAYÜZÜ (WEB TASARIMI)
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
    [
        "Dönem Başı Ödemeli (Peşin - äx)",
        "Dönem Sonu Ödemeli (ax)",
        "Ertelemeli Dönem Başı (n|äx)",
        "Ertelemeli Dönem Sonu (n|ax)",
        "n Yıl Vadeli - Dönem Başı",
        "n Yıl Vadeli - Dönem Sonu",
    ]
)

# annuity_type_input metnini math_engine'in anlayacağı annuity_type koduna çevir
_ANNUITY_TYPE_MAP = {
    "Dönem Başı Ödemeli (Peşin - äx)": "due",
    "Dönem Sonu Ödemeli (ax)": "immediate",
    "Ertelemeli Dönem Başı (n|äx)": "deferred_due",
    "Ertelemeli Dönem Sonu (n|ax)": "deferred_immediate",
    "n Yıl Vadeli - Dönem Başı": "term_due",
    "n Yıl Vadeli - Dönem Sonu": "term_immediate",
}
annuity_type = _ANNUITY_TYPE_MAP[annuity_type_input]

# Ertelemeli veya vadeli seçildiyse kullanıcıdan ek "n" girdisi al
deferral_years = 0
term_years = 0
if annuity_type.startswith("deferred"):
    deferral_years = st.sidebar.number_input("Erteleme Süresi n (Yıl)", min_value=1, max_value=30, value=5, step=1)
elif annuity_type.startswith("term"):
    term_years = st.sidebar.number_input("Vade Süresi n (Yıl)", min_value=1, max_value=30, value=10, step=1)

# Hesaplamaları ve Simülasyonu Tetikle
trh_data = get_trh2010_data()
engine = ActuarialEngine(trh_data, interest_rate)

annuity_val = engine.calculate_single_premium_annuity(
    age, gender, annuity_type,
    deferral_period=deferral_years,
    term_years=term_years,
)
sim_results = run_cached_simulation(trh_data, age, gender, cohort_size)

# Hesaplanan Değerler (Kart Tasarımları)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Aktüeryal Anüite Faktörü",
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