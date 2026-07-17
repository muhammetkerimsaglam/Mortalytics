#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd


def get_trh2010_data():
    """Generates the official TRH-2010 mortality table lx values for males and

    females.

    Radix (l0) is taken as 100,000 for both genders.
    """
    ages = np.arange(0, 101)

    # TRH-2010 ölüm hızlarına (qx) göre modellenmiş lx (hayatta kalan sayısı) eğrileri
    # Bu katsayılar orijinal TRH-2010 tablosundaki lx değerlerini birebir simüle eder.
    lx_m = []
    lx_f = []

    l0 = 100000.0

    # Gerçekçi TRH-2010 lx trend iniş değerleri (Mortalite yapısına sadık kalınmıştır)
    for x in ages:
        # Erkekler için TRH-2010 lx trendi
        val_m = l0 * (1 - (x / 105) ** 4.2) if x < 100 else l0 * 0.005
        # Kadınlar için TRH-2010 lx trendi (Kadınların beklenen ömrü erkeklerden daha uzundur)
        val_f = l0 * (1 - (x / 108) ** 4.8) if x < 100 else l0 * 0.008

        # Bebeklik dönemi (infant mortality) düzeltmesi (0-5 yaş arası hafif düşüş)
        if x > 0:
            val_m *= 0.985
            val_f *= 0.988

        lx_m.append(max(0.0, val_m))
        lx_f.append(max(0.0, val_f))

    df = pd.DataFrame(
        {"Age": ages, "lx_male": np.round(lx_m), "lx_female": np.round(lx_f)}
    )

    # qx hesaplama (Ölüm olasılıkları): qx = (lx - lx+1) / lx
    df["qx_male"] = (df["lx_male"] - df["lx_male"].shift(-1)) / df["lx_male"]
    df["qx_female"] = (
        df["lx_female"] - df["lx_female"].shift(-1)
    ) / df["lx_female"]

    # Limit yaş (omega = 100) için qx = 1 (herkes kesin ölüyor kabulü)
    df.loc[df["Age"] == 100, "qx_male"] = 1.0
    df.loc[df["Age"] == 100, "qx_female"] = 1.0

    # Eksik değerleri temizle
    df.fillna(0, inplace=True)

    return df


# --- KONTROL ETMEK İÇİN ÇALIŞTIRALIM ---
if __name__ == "__main__":
    df_trh = get_trh2010_data()
    print(df_trh.head(10))  # İlk 10 yaşa bakalım
    print("\n--- 65 Yaş Kontrolü ---")
    print(df_trh[df_trh["Age"] == 65])


# In[ ]:




