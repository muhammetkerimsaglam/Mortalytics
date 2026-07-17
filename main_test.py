#!/usr/bin/env python
# coding: utf-8
"""
main_test.py
=============
Notebook'tan dışa aktarılmış, manuel inceleme/demo scripti.

Bu dosya artık hesaplama sınıflarını KENDİ İÇİNDE tanımlamıyor — hepsi
`math_engine.py`'dan import ediliyor (tek gerçek kaynak). Bu sayede burada
gördüğünüz sonuçlar, Streamlit uygulamasında (app.py) gördüğünüz sonuçlarla
HER ZAMAN birebir tutarlı olur.
"""

from math_engine import generate_trh2010_data, ActuarialEngine, CohortSimulator

# In[3]:

# TRH-2010 (sentetik/yaklaşık) veriyi çekelim
trh_data = generate_trh2010_data()

# Aktüeryal motoru başlatalım (%9 teknik faiz oranı ile)
engine = ActuarialEngine(trh_data, interest_rate=0.09)

# 65 yaşındaki bir erkek için peşin ömür boyu anüite değerini hesaplayalım (ä_65)
annuity_val = engine.calculate_single_premium_annuity(age=65, gender="male", annuity_type="due")

print("=== 1. AKTÜERYAL DEĞERLER (SENTETİK/YAKLAŞIK TRH-2010 MODELİ ÜZERİNDEN) ===")
print(f"%9 Faiz ile ä_65 Değeri: {annuity_val:.4f}")
print(f"Her yıl 100.000 TL ödemek için kişi başı gereken rezerv: {100000 * annuity_val:,.2f} TL\n")

# Yeni eklenen anüite tiplerini de gösterelim
deferred_val = engine.calculate_single_premium_annuity(age=65, gender="male", annuity_type="deferred_due", deferral_period=10)
term_val = engine.calculate_single_premium_annuity(age=65, gender="male", annuity_type="term_due", term_years=10)
print(f"10 Yıl Ertelemeli (n|äx): {deferred_val:.4f}")
print(f"10 Yıl Vadeli (n_äx):     {term_val:.4f}")
print(f"Toplam (vadeli + ertelemeli, äx'e eşit olmalı): {term_val + deferred_val:.4f}  (äx = {annuity_val:.4f})\n")

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

fig.update_layout(
    title=dict(
        text="Mortalytics: TRH-2010 Esintili Dinamik Kohort Simülasyonu (65 Yaş, 10.000 Kişi)",
        font=dict(size=18, color="#1f77b4")
    ),
    xaxis_title="Yaş (x)",
    legend=dict(x=0.01, y=0.99, bgcolor="rgba(255, 255, 255, 0.5)"),
    hovermode="x unified",
    template="plotly_white",
    width=1000,
    height=550
)

fig.update_yaxes(title_text="Aktif Hayatta Kalan Birey Sayısı", secondary_y=False)
fig.update_yaxes(title_text="Yıllık Vefat Sayısı", secondary_y=True)

fig.show()

# In[ ]: