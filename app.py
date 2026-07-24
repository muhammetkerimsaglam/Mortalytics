import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from math_engine import (
    generate_trh2010_data, ActuarialEngine, CohortSimulator,
    run_reserve_distribution, calculate_stochastic_annuity,
)

# Sayfa Genişlik ve Başlık Ayarları
st.set_page_config(
    page_title="Mortalytics: Emeklilik Rezervi Hesaplama & Risk Simülasyonu (Demo)",
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


@st.cache_data  # n_paths sayısı kadar tekrar ağır bir işlem, önbelleklenir
def run_cached_stochastic_annuity(
    mortality_df: pd.DataFrame,
    age: int,
    gender: str,
    annuity_type: str,
    a: float,
    b: float,
    sigma: float,
    deferral_period: int,
    term_years: int,
    n_paths: int,
):
    """calculate_stochastic_annuity() için cache'lenmiş sarmalayıcı."""
    return calculate_stochastic_annuity(
        mortality_df, age, gender, annuity_type, a, b, sigma,
        deferral_period, term_years, n_paths,
    )


def _format_tl_short(value: float) -> str:
    """Büyük TL tutarlarını Türkçe okunabilir bir formata çevirir (milyar/milyon)."""
    def _tr_decimal(num: float) -> str:
        return f"{num:.2f}".replace(".", ",")

    if abs(value) >= 1_000_000_000:
        return f"{_tr_decimal(value / 1_000_000_000)} milyar TL"
    elif abs(value) >= 1_000_000:
        return f"{_tr_decimal(value / 1_000_000)} milyon TL"
    return f"{value:,.0f} TL".replace(",", ".")


# ==============================================================================
# STREAMLIT ARAYÜZÜ (WEB TASARIMI)
# ==============================================================================

# Başlık Kısmı
st.title("📊 Mortalytics")
st.subheader("Emekliliğe Ne Kadar Rezerv Ayırmak Gerekir?")
st.markdown(
    "Bu uygulama, bir kişinin emekliliğinde her yıl düzenli bir ödeme "
    "alabilmesi için **bugünden ne kadar para ayırması gerektiğini** hesaplar. "
    "Ayrıca aynı yaştaki büyük bir grup insan için bu hesabın **ne kadar "
    "güvenilir** olduğunu da gösterir."
)

st.warning(
    "**Bu bir demo/eğitim projesidir.** Kullanılan yaşam tablosu, TSB/SBM tarafından "
    "yayınlanan **resmi TRH-2010 tablosu değildir**; TRH-2010'un genel eğilimini "
    "(kadın-erkek farkı, yaşa bağlı artan ölüm oranı) yansıtan **sentetik/yaklaşık bir "
    "modeldir**. Gerçek aktüeryal, sigortacılık veya hukuki (tazminat vb.) hesaplamalarda "
    "kullanılmamalıdır.",
    icon="⚠️"
)

view_mode = st.radio(
    "Görünüm seç:",
    ["📖 Basit Anlatım (Hikaye Modu)", "🛠️ Gelişmiş Görünüm (Tüm Ayarlar)"],
    horizontal=True,
)
is_story_mode = view_mode.startswith("📖")

st.divider()

# Sabit veri her iki modda da aynı
trh_data = get_trh2010_data()

# ==============================================================================
# ORTAK SABİTLER (Basit modda kullanıcıdan istenmeyen, arka planda otomatik
# seçilen teknik parametreler)
# ==============================================================================
_DEFAULT_INTEREST_RATE = 0.09
_DEFAULT_COHORT_SIZE = 10000
_DEFAULT_N_SIMULATIONS = 200


if is_story_mode:
    # ==========================================================================
    # 📖 BASİT ANLATIM (HİKAYE MODU)
    # Sadece 3 basit soru; geri kalan her şey arka planda otomatik.
    # ==========================================================================
    st.write("### Sadece birkaç şey soralım 👇")
    q1, q2, q3 = st.columns(3)
    with q1:
        gender_input = st.selectbox("Cinsiyetin", ["Erkek", "Kadın"], index=0)
        gender = "male" if gender_input == "Erkek" else "female"
    with q2:
        age = st.slider("Kaç yaşında emekli olmayı planlıyorsun?", min_value=18, max_value=90, value=65, step=1)
    with q3:
        annuity_pay = st.number_input(
            "Emeklilikte yılda ne kadar gelir istersin? (TL)",
            min_value=1000, value=100000, step=5000
        )

    # Arka planda sabit/varsayılan teknik ayarlar
    interest_rate = _DEFAULT_INTEREST_RATE
    annuity_type = "due"
    deferral_years = 0
    term_years = 0
    cohort_size = _DEFAULT_COHORT_SIZE
    n_simulations = _DEFAULT_N_SIMULATIONS

    engine = ActuarialEngine(trh_data, interest_rate)
    annuity_val = engine.calculate_single_premium_annuity(age, gender, annuity_type)
    sim_results = run_cached_simulation(trh_data, age, gender, cohort_size)

    reserve_needed = annuity_pay * annuity_val

    st.divider()
    st.write("### 💰 Senin İçin Sonuç")
    st.markdown(
        f"**{age} yaşında emekli olup her yıl {annuity_pay:,.0f} TL almak istiyorsun.** "
        "Bunu karşılayabilmek için bugünden ayırman gereken tutar:"
    )
    st.metric(label="Bugünden Ayırman Gereken Tutar", value=f"{reserve_needed:,.2f} TL")

    st.divider()

    # --- Basit hikaye anlatımı: hayatta kalma ---
    st.write("### 👥 Aynı Durumdaki Bir Grup Ne Olur?")
    horizon_years = min(20, len(sim_results) - 1)
    survivors_at_horizon = int(sim_results.iloc[horizon_years]["Survivors"])
    horizon_age = age + horizon_years
    survival_pct = survivors_at_horizon / cohort_size * 100

    st.markdown(
        f"Seninle aynı yaşta ve aynı cinsiyette **{cohort_size:,.0f} kişilik** örnek bir "
        f"grup düşünelim. **{horizon_age} yaşına** geldiklerinde, bu gruptan yaklaşık "
        f"**{survivors_at_horizon:,.0f} kişi (%{survival_pct:.0f})** hâlâ hayatta olacak. "
        "İşte hesaplanan rezerv, tam olarak bu tür belirsizliği hesaba katıyor."
    )

    with st.expander("📈 Grafiği Görmek İster misin?"):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=sim_results["Age"],
                y=sim_results["Survivors"],
                name="Hayatta Olanlar",
                line=dict(color="#2ca02c", width=3),
                mode="lines+markers",
                hovertemplate="<b>Yaş:</b> %{x}<br><b>Hayatta Olan:</b> %{y:,.0f} kişi<extra></extra>"
            )
        )
        fig.update_layout(
            xaxis_title="Yaş",
            yaxis_title="Hayatta Olan Kişi Sayısı",
            template="plotly_white",
            height=420,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Basit risk özeti (Monte Carlo'yu tek cümleyle anlat) ---
    st.write("### 🎲 Bu Hesap Ne Kadar Güvenilir?")
    with st.spinner("Yüzlerce farklı ihtimal deneniyor..."):
        reserve_costs = run_cached_reserve_distribution(
            trh_data, age, gender, cohort_size, interest_rate, annuity_pay,
            annuity_type, deferral_years, term_years, n_simulations,
        )
    reserve_set_aside = cohort_size * annuity_pay * annuity_val
    exceedance_prob = float((reserve_costs > reserve_set_aside).mean())

    if exceedance_prob < 5:
        risk_comment = "Bu oldukça düşük bir ihtimal — ayrılan tutar genelde yeterli görünüyor."
    elif exceedance_prob < 20:
        risk_comment = "Küçük ama göz ardı edilmeyecek bir ihtimal — biraz daha fazla ayırmak isteyebilirsin."
    else:
        risk_comment = "Bu epey yüksek bir ihtimal — daha fazla rezerv ayırmayı düşünebilirsin."

    st.markdown(
        f"Aynı hesaplamayı **{n_simulations} farklı ihtimalle** yeniden denedik. "
        f"Bunların **%{exceedance_prob * 100:.0f} 'lık kısmında**, bugün ayırdığın tutar yeterli olmuyor. "
        f"{risk_comment}"
    )

    st.divider()
    st.info(
        "💡 Faiz oranını değiştirmek, farklı ödeme şekilleri (ertelemeli/vadeli) denemek "
        "veya tüm teknik grafikleri görmek istersen, yukarıdan **🛠️ Gelişmiş Görünüm**'e geçebilirsin."
    )

else:
    # ==========================================================================
    # 🛠️ GELİŞMİŞ GÖRÜNÜM (TÜM AYARLAR VE TEKNİK DETAYLAR)
    # ==========================================================================

    # Yan Panel (Giriş Parametreleri)
    st.sidebar.header("⚙️ Simülasyon Parametreleri")

    gender_input = st.sidebar.selectbox("Cinsiyet", ["Erkek", "Kadın"], index=0)
    gender = "male" if gender_input == "Erkek" else "female"

    age = st.sidebar.slider("Giriş / Emeklilik Yaşı (x)", min_value=18, max_value=90, value=65, step=1)

    interest_rate_pct = st.sidebar.slider("Teknik Faiz Oranı (%)", min_value=0.0, max_value=20.0, value=9.0, step=0.5)
    interest_rate = interest_rate_pct / 100.0

    interest_model = st.sidebar.radio(
        "Faiz Zamanla Değişsin mi?",
        ["Sabit Kalsın", "Değişsin (Gelişmiş)"],
        horizontal=True,
        help="'Değişsin' seçilirse, faiz oranı yukarıda seçtiğiniz seviye "
             "etrafında zamanla rastgele dalgalanan bir model (teknik adı: CIR) kullanılır."
    )

    cir_n_paths = 0
    if interest_model == "Değişsin (Gelişmiş)":
        st.sidebar.caption(
            "Bu modelin arka planda kullandığı parametreler: a=0,2 (ortalamaya dönüş hızı), "
            "σ=0,02 (oynaklık), b=yukarıdaki teknik faiz oranı. Bu değerler literatürde sık "
            "kullanılan **temsili** parametrelerdir, gerçek piyasa verisiyle kalibre edilmemiştir."
        )
        cir_n_paths = st.sidebar.slider(
            "Faiz Senaryosu Sayısı", min_value=100, max_value=1000, value=500, step=100
        )

    cohort_size = st.sidebar.number_input(
        "Aynı Yaştaki Grup Büyüklüğü (Kişi)",
        min_value=100, max_value=100000, value=10000, step=500,
        help="Aynı yaşta, aynı özelliklerde kaç kişiyi birlikte simüle edelim? "
             "(Aktüeryal terimle: kohort büyüklüğü)"
    )

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
    st.sidebar.subheader("🎲 Bu Hesap Ne Kadar Güvenilir?")
    n_simulations = st.sidebar.slider(
        "Kaç Kez Tekrar Deneyelim?",
        min_value=50, max_value=500, value=200, step=50,
        help="Aynı grubu kaç kez baştan simüle edip sonuçların ne kadar "
             "değiştiğine bakacağız. Daha yüksek sayı daha net bir tablo verir "
             "ama hesaplama biraz daha uzun sürer. (Teknik adı: Monte Carlo tekrar sayısı)"
    )

    # Hesaplamaları ve Simülasyonu Tetikle
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

    # Ana Vitrin Metriği: Kullanıcı için tek, anlaşılır sonuç
    st.write("### 💰 Sonuç")
    st.markdown(
        f"**{age} yaşında** bu ödemeyi alabilmek için bugünden ayırman gereken tutar:"
    )
    st.metric(
        label=f"Kişi Başına Gereken Rezerv ({annuity_label})",
        value=f"{annuity_pay * annuity_val:,.2f} TL"
    )

    with st.expander("🔍 Teknik Detayları Göster (Anüite Faktörü & Toplam Portföy Rezervi)"):
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.metric(
                label=annuity_label,
                value=f"{annuity_val:.4f}",
                help="Aktüeryal terimle 'anüite faktörü': 1 TL'lik yıllık ödemenin "
                     "bugünkü karşılığı. Yukarıdaki sonuç bu faktörün ödeme tutarıyla çarpımıdır."
            )
        with detail_col2:
            st.metric(
                label="Aynı Gruptaki Herkes İçin Toplam Rezerv",
                value=f"{cohort_size * annuity_pay * annuity_val:,.2f} TL",
                help="Yukarıdaki bireysel tutarın, seçtiğin grup büyüklüğü (kohort) "
                     "kadar kişi için toplamı."
            )

    st.divider()

    # Plotly Grafiği
    st.write("### 📈 Zaman İçinde Gruptaki Kişilere Ne Oluyor?")
    st.markdown(
        f"**{age} yaşında** başlayan **{cohort_size:,.0f} kişilik** bir grubu ele alalım. "
        "Yaş ilerledikçe grupta kaç kişinin hayatta kaldığını ve o yıl kaç kişinin "
        "vefat ettiğini aşağıda görebilirsin."
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Hayatta Kalanlar Çizgisi
    fig.add_trace(
        go.Scatter(
            x=sim_results["Age"],
            y=sim_results["Survivors"],
            name="Hayatta Olanlar",
            line=dict(color="#2ca02c", width=3),
            mode="lines+markers",
            hovertemplate="<b>Yaş:</b> %{x}<br><b>Hayatta Olan:</b> %{y:,.0f} kişi<extra></extra>"
        ),
        secondary_y=False,
    )

    # Vefat Edenler Barı
    fig.add_trace(
        go.Bar(
            x=sim_results["Age"],
            y=sim_results["Deaths_This_Year"],
            name="O Yıl Vefat Eden",
            marker_color="rgba(214, 39, 40, 0.7)",
            hovertemplate="<b>Yaş:</b> %{x}<br><b>Vefat Eden:</b> %{y:,.0f} kişi<extra></extra>"
        ),
        secondary_y=True,
    )

    fig.update_layout(
        xaxis_title="Yaş",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255, 255, 255, 0.5)"),
        hovermode="x unified",
        template="plotly_white",
        height=500
    )

    fig.update_yaxes(title_text="Hayatta Olan Kişi Sayısı", secondary_y=False)
    fig.update_yaxes(title_text="O Yıl Vefat Eden Kişi Sayısı", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ==========================================================================
    # MONTE CARLO REZERV YETERLİLİĞİ DAĞILIMI
    # ==========================================================================
    st.write("### 🎲 Ayrılan Rezerv Yeterli mi?")
    st.markdown(
        f"Yukarıdaki sonuç, işlerin 'ortalama' gittiği tek bir senaryoyu gösteriyordu. "
        f"Gerçekte kimin ne zaman vefat edeceği baştan bilinmez — bu yüzden aynı grubu "
        f"**{n_simulations} farklı ihtimalle** yeniden 'yaşatıp', her seferinde toplam "
        f"ödeme maliyetinin ne kadar değiştiğine bakıyoruz. Amaç: ayrılan rezervin "
        f"gerçekte yetip yetmeyeceğini görmek."
    )

    reserve_costs = run_cached_reserve_distribution(
        trh_data, age, gender, cohort_size, interest_rate, annuity_pay,
        annuity_type, deferral_years, term_years, n_simulations,
    )
    reserve_set_aside = cohort_size * annuity_pay * annuity_val
    exceedance_prob = float((reserve_costs > reserve_set_aside).mean())
    p5 = float(pd.Series(reserve_costs).quantile(0.05))
    p95 = float(pd.Series(reserve_costs).quantile(0.95))

    mc_col1, mc_col2, mc_col3 = st.columns(3)
    with mc_col1:
        st.metric(
            "Rezervin Yetersiz Kalma İhtimali",
            f"%{exceedance_prob * 100:.1f}",
            help="Denediğimiz ihtimallerin yüzde kaçında, gerçekleşen toplam ödeme "
                 "maliyeti önceden ayrılan rezervi aştı?"
        )
    with mc_col2:
        st.metric("Ortalama Gerçekleşen Maliyet", _format_tl_short(reserve_costs.mean()))
    with mc_col3:
        st.metric(
            "Olası Aralık (%5 – %95)",
            f"{_format_tl_short(p5)} – {_format_tl_short(p95)}",
            help=f"İhtimallerin %90'ı bu aralıkta kaldı. Tam değerler: {p5:,.0f} TL – {p95:,.0f} TL"
        )

    hist_fig = go.Figure()
    hist_fig.add_trace(go.Histogram(
        x=reserve_costs,
        nbinsx=40,
        marker_color="rgba(31, 119, 180, 0.75)",
        name="Gerçekleşen Maliyet Dağılımı",
        hovertemplate="Aralık: %{x:,.0f} TL<br>Kaç Kez Bu Aralığa Düştü: %{y}<extra></extra>",
    ))
    hist_fig.add_vline(
        x=reserve_set_aside,
        line_width=3,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="Ayrılan Rezerv",
        annotation_position="top",
    )
    hist_fig.update_layout(
        xaxis_title="Gerçekleşen Toplam Ödeme Maliyeti (TL)",
        yaxis_title="Kaç Kez Bu Sonuç Çıktı",
        template="plotly_white",
        height=420,
        showlegend=False,
    )
    st.plotly_chart(hist_fig, use_container_width=True)

    st.caption(
        "💡 Grup büyüklüğünü (Aynı Yaştaki Grup Büyüklüğü) değiştirerek dene: "
        "grup büyüdükçe sonuçlar birbirine daha çok benzer ve dağılım daralır; "
        "küçük gruplarda ise belirsizlik çok daha yüksektir."
    )

    st.divider()

    # ==========================================================================
    # STOKASTİK FAİZ ORANI MODELİ (CIR)
    # ==========================================================================
    if interest_model == "Değişsin (Gelişmiş)":
        st.write("### 📈 Faiz Oranı Sabit Kalmasaydı Ne Olurdu?")
        st.markdown(
            "Şimdiye kadar faiz oranını sabit kabul ettik. Burada, faizin gelecekte "
            "zamanla yukarı-aşağı dalgalanabileceğini varsayıyoruz (ölüm/yaşam tarafı "
            "yine sabit kalıyor, sadece faiz değişiyor). Aşağıdaki dağılım, "
            f"**{cir_n_paths} farklı faiz senaryosu** denendiğinde anüite faktörünün "
            "nasıl değişebileceğini gösteriyor. *(Teknik adı: CIR modeli)*"
        )

        stochastic_vals = run_cached_stochastic_annuity(
            trh_data, age, gender, annuity_type,
            0.2, interest_rate, 0.02,  # a, b, sigma (b = kullanıcının seçtiği teknik faiz)
            deferral_years, term_years, cir_n_paths,
        )

        cir_col1, cir_col2, cir_col3 = st.columns(3)
        with cir_col1:
            st.metric(
                "Ortalama Anüite Faktörü (Faiz Değişken Olsaydı)",
                f"{stochastic_vals.mean():.4f}",
                delta=f"{stochastic_vals.mean() - annuity_val:+.4f} (sabit faize göre)",
                help="Sabit faizle hesaplanan değerle karşılaştırma."
            )
        with cir_col2:
            st.metric("Sonuçların Ne Kadar Dağıldığı (Std. Sapma)", f"{stochastic_vals.std():.4f}")
        with cir_col3:
            cir_p5 = float(pd.Series(stochastic_vals).quantile(0.05))
            cir_p95 = float(pd.Series(stochastic_vals).quantile(0.95))
            st.metric("Olası Aralık (%5 – %95)", f"{cir_p5:.4f} – {cir_p95:.4f}")

        cir_fig = go.Figure()
        cir_fig.add_trace(go.Histogram(
            x=stochastic_vals,
            nbinsx=40,
            marker_color="rgba(148, 103, 189, 0.75)",
            name="Faiz Değişken Olsaydı Dağılımı",
            hovertemplate="Değer: %{x:.4f}<br>Kaç Senaryoda Çıktı: %{y}<extra></extra>",
        ))
        cir_fig.add_vline(
            x=annuity_val,
            line_width=3,
            line_dash="dash",
            line_color="#d62728",
            annotation_text="Sabit Faiz Değeri",
            annotation_position="top",
        )
        cir_fig.update_layout(
            xaxis_title="Anüite Faktörü",
            yaxis_title="Kaç Senaryoda Bu Sonuç Çıktı",
            template="plotly_white",
            height=420,
            showlegend=False,
        )
        st.plotly_chart(cir_fig, use_container_width=True)

        st.caption(
            "💡 Faiz hiç dalgalanmasaydı (oynaklık sıfır olsaydı), bu dağılım tek bir "
            "çizgiye (sabit faiz değerine) çökerdi — bu proje bunu bir testle doğrular. "
            "Küçük bir dalgalanmayla bile anüite faktöründe belirgin bir belirsizlik "
            "oluştuğunu görebilirsin."
        )

        st.divider()

    # Veri Tablosu İndirme Seçeneği
    st.write("### 📋 Yıl Yıl Detaylı Sonuçlar")
    st.dataframe(sim_results, use_container_width=True)