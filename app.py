import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from math_engine import generate_trh2010_data, ActuarialEngine, CohortSimulator, run_reserve_distribution

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


@st.cache_data  # n_simulations sayısı kadar tekrar ağır bir işlem, önbelleklenir
def run_cached_reserve_distribution(
    mortality_df: pd.DataFrame,
    start_age: int,
    gender: str,
    cohort_size: int,
    interest_rate: float,
    annuity_pay: float,
    annuity_type: str,
    deferral_period: int,
    term_years: int,
    n_simulations: int,
):
    """run_reserve_distribution() için cache'lenmiş sarmalayıcı."""
    return run_reserve_distribution(
        mortality_df, start_age, gender, cohort_size, interest_rate,
        annuity_pay, annuity_type, deferral_period, term_years, n_simulations,
    )


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

st.sidebar.divider()
st.sidebar.subheader("📐 Anüite Ayarları")

# Tek uzun bir dropdown yerine iki kısa adıma bölündü: hem her zaman tam
# görünür (kaydırma gerektirmez) hem de "n Yıl Vadeli" gibi seçeneklerin
# fark edilmeden gizli kalmasını önler.
annuity_shape = st.sidebar.selectbox(
    "Anüite Şekli",
    ["Ömür Boyu (Whole Life)", "Ertelemeli (Deferred)", "n Yıl Vadeli (Term)"],
)

timing_input = st.sidebar.radio(
    "Ödeme Zamanlaması",
    ["Dönem Başı (Peşin)", "Dönem Sonu"],
)
_is_due = timing_input.startswith("Dönem Başı")

_SHAPE_TO_BASE_TYPE = {
    "Ömür Boyu (Whole Life)": ("due", "immediate"),
    "Ertelemeli (Deferred)": ("deferred_due", "deferred_immediate"),
    "n Yıl Vadeli (Term)": ("term_due", "term_immediate"),
}
annuity_type = _SHAPE_TO_BASE_TYPE[annuity_shape][0 if _is_due else 1]

# Ertelemeli veya vadeli seçildiyse kullanıcıdan ek "n" girdisi al
deferral_years = 0
term_years = 0
if annuity_type.startswith("deferred"):
    deferral_years = st.sidebar.number_input("Erteleme Süresi n (Yıl)", min_value=1, max_value=30, value=5, step=1)
elif annuity_type.startswith("term"):
    term_years = st.sidebar.number_input("Vade Süresi n (Yıl)", min_value=1, max_value=30, value=10, step=1)

st.sidebar.divider()
st.sidebar.subheader("🎲 Risk Analizi (Monte Carlo)")
n_simulations = st.sidebar.slider(
    "Simülasyon Tekrar Sayısı",
    min_value=50, max_value=500, value=200, step=50,
    help="Aynı kohortu kaç kez tekrar simüle edip dağılımını çıkaracağımız. "
         "Daha yüksek sayı daha pürüzsüz bir dağılım verir ama daha yavaş çalışır."
)

# Hesaplamaları ve Simülasyonu Tetikle
trh_data = get_trh2010_data()
engine = ActuarialEngine(trh_data, interest_rate)

annuity_val = engine.calculate_single_premium_annuity(
    age, gender, annuity_type,
    deferral_period=deferral_years,
    term_years=term_years,
)
sim_results = run_cached_simulation(trh_data, age, gender, cohort_size)

# Seçilen anüite tipini kullanıcıya net gösteren dinamik etiket
_timing_short = "Peşin" if _is_due else "Dönem Sonu"
if annuity_shape == "Ömür Boyu (Whole Life)":
    annuity_label = f"Ömür Boyu Anüite Faktörü ({_timing_short})"
elif annuity_shape == "Ertelemeli (Deferred)":
    annuity_label = f"{deferral_years} Yıl Ertelemeli Anüite Faktörü ({_timing_short})"
else:
    annuity_label = f"{term_years} Yıl Vadeli Anüite Faktörü ({_timing_short})"

# Hesaplanan Değerler (Kart Tasarımları)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label=annuity_label,
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

st.divider()

# ==============================================================================
# MONTE CARLO REZERV YETERLİLİĞİ DAĞILIMI
# ==============================================================================
st.write("### 🎲 Rezerv Yeterliliği Dağılımı (Monte Carlo Risk Analizi)")
st.markdown(
    f"Yukarıdaki kohort, tek bir rastgele gerçekleşmeyi gösteriyordu. Burada aynı "
    f"kohort parametreleriyle simülasyonu **{n_simulations} kez** tekrarlıyoruz ve her "
    f"seferinde gerçekleşen toplam ödeme maliyetinin ne kadar değiştiğine bakıyoruz. "
    f"Amaç: ayrılan rezervin gerçekte yeterli olup olmayacağını görmek."
)

reserve_costs = run_cached_reserve_distribution(
    trh_data, age, gender, cohort_size, interest_rate, annuity_pay,
    annuity_type, deferral_years, term_years, n_simulations,
)
reserve_set_aside = cohort_size * annuity_pay * annuity_val
exceedance_prob = float((reserve_costs > reserve_set_aside).mean())
p5 = float(pd.Series(reserve_costs).quantile(0.05))
p95 = float(pd.Series(reserve_costs).quantile(0.95))

def _format_tl_short(value: float) -> str:
    """Büyük TL tutarlarını okunabilir/kısa bir formata çevirir (Milyar/Milyon)."""
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B TL"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M TL"
    return f"{value:,.0f} TL"


mc_col1, mc_col2, mc_col3 = st.columns(3)
with mc_col1:
    st.metric(
        "Ayrılan Rezervin Yetersiz Kalma Olasılığı",
        f"%{exceedance_prob * 100:.1f}",
        help="Simülasyonların yüzde kaçında, gerçekleşen toplam ödeme maliyeti "
             "önceden ayrılan (deterministik) rezervi aştı?"
    )
with mc_col2:
    st.metric("Ortalama Gerçekleşen Maliyet", _format_tl_short(reserve_costs.mean()))
with mc_col3:
    st.metric(
        "%5 – %95 Aralığı",
        f"{_format_tl_short(p5)} – {_format_tl_short(p95)}",
        help=f"Tam değerler: {p5:,.0f} TL – {p95:,.0f} TL"
    )

hist_fig = go.Figure()
hist_fig.add_trace(go.Histogram(
    x=reserve_costs,
    nbinsx=40,
    marker_color="rgba(31, 119, 180, 0.75)",
    name="Gerçekleşen Maliyet Dağılımı",
    hovertemplate="Aralık: %{x:,.0f} TL<br>Simülasyon Sayısı: %{y}<extra></extra>",
))
hist_fig.add_vline(
    x=reserve_set_aside,
    line_width=3,
    line_dash="dash",
    line_color="#d62728",
    annotation_text="Ayrılan Rezerv (Deterministik)",
    annotation_position="top",
)
hist_fig.update_layout(
    xaxis_title="Gerçekleşen Toplam Ödeme Maliyeti (TL)",
    yaxis_title="Simülasyon Sayısı",
    template="plotly_white",
    height=420,
    showlegend=False,
)
st.plotly_chart(hist_fig, use_container_width=True)

st.caption(
    "💡 Kohort sayısını (Başlangıç Kohort Sayısı) düşürüp yükselterek deneyin: "
    "kohort büyüdükçe dağılım daralır (büyük sayılar kanunu — havuzlama riski azaltır), "
    "küçük kohortlarda ise belirsizlik çok daha yüksektir."
)

st.divider()

# Veri Tablosu İndirme Seçeneği
st.write("### 📋 Simülasyon Veri Akışı Detayları")
st.dataframe(sim_results, use_container_width=True)