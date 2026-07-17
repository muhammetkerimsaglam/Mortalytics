#!/usr/bin/env python
# coding: utf-8
"""
trh2010_generator.py
======================
GERİYE DÖNÜK UYUMLULUK İÇİN İNCE SARMALAYICI (thin wrapper).

Bu dosya artık veri üretme mantığını KENDİ İÇİNDE barındırmıyor. Gerçek
kod `math_engine.generate_trh2010_data()` içinde tutuluyor (tek gerçek
kaynak / single source of truth). Bu dosya sadece eski/alışılmış
`from trh2010_generator import get_trh2010_data` import yolunun
kırılmaması için burada duruyor.

ÖNEMLİ VERİ NOTU: Üretilen tablo TSB/SBM'nin RESMİ TRH-2010 tablosu
DEĞİLDİR — TRH-2010'un genel eğilimini yansıtan sentetik/yaklaşık bir
modeldir. Detaylar için math_engine.py'daki docstring'e bakınız.
"""

from math_engine import generate_trh2010_data as get_trh2010_data

__all__ = ["get_trh2010_data"]


# --- KONTROL ETMEK İÇİN ÇALIŞTIRALIM ---
if __name__ == "__main__":
    df_trh = get_trh2010_data()
    print(df_trh.head(10))  # İlk 10 yaşa bakalım
    print("\n--- 65 Yaş Kontrolü ---")
    print(df_trh[df_trh["Age"] == 65])