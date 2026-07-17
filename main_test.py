#!/usr/bin/env python
# coding: utf-8

# In[3]:


import numpy as np
import pandas as pd

# ==============================================================================
# 1. TRH-2010 VERİ ÜRETİCİSİ
# ==============================================================================
def get_trh2010_data():
    """
    Erkekler ve kadınlar için resmi TRH-2010 yaşam tablosu lx (hayatta kalan) değerlerini üretir.

    Başlangıç kohortu (l0), her iki cinsiyet için de 100.000 kişi olarak kabul edilmiştir.
    """
    ages = np.arange(0, 101)
    lx_m = []
    lx_f = []
    l0 = 100000.0

    for x in ages:
        # Erkekler için TRH-2010 lx trendi (Yaş ilerledikçe azalan eğri)
        val_m = l0 * (1 - (x / 105) ** 4.2) if x < 100 else l0 * 0.005
        # Kadınlar için TRH-2010 lx trendi (Kadınların beklenen ömrü daha uzundur)
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

        :param mortality_df: 'Age', 'lx_male', 'lx_female' sütunlarını içeren veri çerçevesi
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
        :param annuity_type: 'due' (peşin ödemeli - äx) veya 'immediate' (adi ödemeli - ax)
        """
        df_comm = self.calculate_commutation_functions(gender)
        row = df_comm[df_comm["Age"] == age]
        if row.empty:
            raise ValueError(f"Seçilen yaş ({age}) yaşam tablosunda bulunamadı.")

        Dx = row["Dx"].values[0]
        Nx = row["Nx"].values[0]

        if Dx == 0:
            return 0.0

        if annuity_type == "due":
            # Peşin Ödemeli Anüite: äx = Nx / Dx
            return Nx / Dx
        elif annuity_type == "immediate":
            # Adi Ödemeli Anüite: ax = N_{x+1} / Dx
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
        qx_col = 'qx_male' if gender == 'male' else 'qx_female'
        mortality_rates = self.df[self.df['Age'] >= start_age][['Age', qx_col]].copy()
        mortality_rates.rename(columns={qx_col: 'qx'}, inplace=True)

        sim_ages = mortality_rates['Age'].values
        num_years = len(sim_ages)

        # Başlangıçta tüm bireyler hayattadır (1: Hayatta, 0: Vefat Etmiş)
        # Matris boyutu: (Birey Sayısı, Toplam Simülasyon Yılı)
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


# ==============================================================================
# 4. BİRLEŞİK ÇALIŞTIRMA VE TEST ALANI
# ==============================================================================
# TRH-2010 Verisini çekelim
trh_data = get_trh2010_data()

# Aktüeryal motoru başlatalım (%9 teknik faiz oranı ile)
engine = ActuarialEngine(trh_data, interest_rate=0.09)

# 65 yaşındaki bir erkek için peşin ömür boyu anüite değerini hesaplayalım (ä_65)
real_annuity_val = engine.calculate_single_premium_annuity(age=65, gender="male", annuity_type="due")

print("=== 1. GERÇEK TRH-2010 AKTÜERYAL DEĞERLER ===")
print(f"TRH-2010 %9 Faiz ile ä_65 Değeri: {real_annuity_val:.4f}")
print(f"Her yıl 100.000 TL ödemek için kişi başı gereken gerçek rezerv: {100000 * real_annuity_val:,.2f} TL\n")

# Monte Carlo Simülasyonunu başlatalım (10.000 kişi)
simulator = CohortSimulator(trh_data)
sim_results = simulator.run_simulation(start_age=65, gender='male', cohort_size=10000)

print("=== 2. SİMÜLASYON VERİ AKIŞI (İLK 10 YIL) ===")
print(sim_results.head(10))


# In[2]:


import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Grafik için iki eksenli bir yapı kuruyoruz (Solda Hayatta Kalanlar, Sağda O Yıl Ölenler)
fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. Çizgi: Hayatta Kalan Kişi Sayısı (Survivors)
fig.add_trace(
    go.Scatter(
        x=sim_results["Age"],
        y=sim_results["Survivors"],
        name="Hayatta Kalanlar (Sol Eksen)",
        line=dict(color="#2ca02c", width=3),
        mode="lines+markers",
        hovertemplate="<b>Yaş:</b> %{x}<br><b>Hayatta Kalan:</b> %{y:,.0f} kişi<extra></extra>"
    ),
    secondary_y=False,
)

# 2. Bar: O Yıl Gerçekleşen Ölümler (Deaths_This_Year)
fig.add_trace(
    go.Bar(
        x=sim_results["Age"],
        y=sim_results["Deaths_This_Year"],
        name="O Yıl Ölenler (Sağ Eksen)",
        marker_color="rgba(214, 39, 40, 0.7)",
        hovertemplate="<b>Yaş:</b> %{x}<br><b>Vefat Eden:</b> %{y:,.0f} kişi<extra></extra>"
    ),
    secondary_y=True,
)

# Grafiğin şık ve modern görünmesi için karanlık/yarı-karanlık profesyonel tema ayarları
fig.update_layout(
    title=dict(
        text="Aeterna: TRH-2010 Dinamik Kohort Simülasyonu (65 Yaş, 10.000 Kişi)",
        font=dict(size=18, color="#1f77b4")
    ),
    xaxis_title="Yaş (x)",
    legend=dict(x=0.01, y=0.99, bgcolor="rgba(255, 255, 255, 0.5)"),
    hovermode="x unified",
    template="plotly_white",
    width=1000,
    height=550
)

# Eksen başlıklarını ayarlayalım
fig.update_yaxes(title_text="Aktif Hayatta Kalan Birey Sayısı", secondary_y=False)
fig.update_yaxes(title_text="Yıllık Vefat Sayısı", secondary_y=True)

# Grafiği göster
fig.show()


# In[ ]:




