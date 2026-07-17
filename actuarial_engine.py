#!/usr/bin/env python
# coding: utf-8
"""
actuarial_engine.py
=====================
GERİYE DÖNÜK UYUMLULUK İÇİN İNCE SARMALAYICI (thin wrapper).

Bu dosya artık hesaplama mantığını KENDİ İÇİNDE barındırmıyor. Projenin
TÜM aktüeryal hesaplama kodu `math_engine.py` içinde tutuluyor (tek gerçek
kaynak / single source of truth). Bu dosya sadece `from actuarial_engine
import ActuarialEngine` şeklindeki eski/alışılmış import yollarının
kırılmaması için burada duruyor.

Bir hesaplama hatası bulursanız veya yeni bir anüite tipi eklemek
isterseniz, DÜZENLEMENİZ GEREKEN DOSYA math_engine.py'dır — burası değil.
"""

from math_engine import ActuarialEngine

__all__ = ["ActuarialEngine"]


# --- MANUEL TEST / KULLANIM ÖRNEĞİ ---
if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    # Basit bir örnek yaşam tablosu (gerçek projede math_engine.generate_trh2010_data() kullanılır)
    ages = np.arange(0, 101)
    lx_sim_m = 100000 * np.exp(-((ages / 75) ** 3))
    lx_sim_f = 100000 * np.exp(-((ages / 80) ** 3))
    dummy_data = pd.DataFrame({"Age": ages, "lx_male": lx_sim_m, "lx_female": lx_sim_f})

    engine = ActuarialEngine(dummy_data, interest_rate=0.09)
    annuity_value = engine.calculate_single_premium_annuity(age=65, gender="male", annuity_type="due")

    print("--- AKTÜERYAL MOTOR TESTİ (math_engine.ActuarialEngine üzerinden) ---")
    print(f"Teknik Faiz Oranı: %{engine.i * 100}")
    print(f"65 yaşındaki erkek için peşin anüite değeri (ä_65): {annuity_value:.4f}")
    print(f"Yıllık 100.000 TL için gereken peşin rezerv: {100000 * annuity_value:,.2f} TL")