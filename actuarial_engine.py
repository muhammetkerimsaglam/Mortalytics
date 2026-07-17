#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd


class ActuarialEngine:

    def __init__(self, mortality_df: pd.DataFrame, interest_rate: float):
        """Actuarial engine to calculate commutation functions and annuities.

        :param mortality_df: DataFrame containing columns ['Age', 'lx_male',
        'lx_female']
        :param interest_rate: Technical interest rate (e.g., 0.09 for 9%)
        """
        self.df = mortality_df.copy()
        self.i = interest_rate
        self.v = 1 / (1 + self.i)  # Discount factor (İskonto faktörü)

    def calculate_commutation_functions(self, gender: str = "male"):
        """Calculates Dx and Nx commutation values based on gender selection."""
        lx_col = "lx_male" if gender == "male" else "lx_female"

        # Dx = v^x * lx
        self.df["Dx"] = (self.v ** self.df["Age"]) * self.df[lx_col]

        # Nx = Sum of Dx from x to omega (TRH-2010 limits)
        # Nx hesaplanırken sondan başa doğru kümülatif toplam alınır
        self.df["Nx"] = self.df["Dx"].iloc[::-1].cumsum().iloc[::-1]

        return self.df
def calculate_single_premium_annuity(self, age: int, gender: str = "male", annuity_type: str = "due", deferral_period: int = 0):
        """Calculates life annuity (Ömür boyu anüite - ax)."""
        
        # Komütasyon değerlerini hesapla
        df_comm = self.calculate_commutation_functions(gender)
        
        # Seçilen yaşın indexini bul
        row = df_comm[df_comm["Age"] == age]
        if row.empty:
            raise ValueError(f"Age {age} not found in mortality table.")
            
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
            
        elif annuity_type == "deferred_due":
            # Ertelemeli Peşin Ödemeli Anüite: n|äx = N_{x+n} / Dx
            deferred_row = df_comm[df_comm["Age"] == (age + deferral_period)]
            if deferred_row.empty:
                return 0.0
            Nx_plus_n = deferred_row["Nx"].values[0]
            return Nx_plus_n / Dx
            
        return 0.0
    	# --- TEST VE KULLANIM ÖRNEĞİ ---
if __name__ == "__main__":
    # Test amaçlı basit bir yaşam tablosu oluşturuyoruz (TRH-2010 temsilidir)
    # Gerçek projede bunu CSV'den okuyacağız.
    ages = np.arange(0, 101)
    # Basit bir lx azalışı simüle edelim (Örn: 100.000 kişiyle başlar, yaşlandıkça azalır)
    lx_sim_m = 100000 * np.exp(-((ages / 75) ** 3))
    lx_sim_f = 100000 * np.exp(-((ages / 80) ** 3))

    dummy_data = pd.DataFrame(
        {"Age": ages, "lx_male": lx_sim_m, "lx_female": lx_sim_f}
    )

    # %9 teknik faiz oranı ile motoru başlatalım
    engine = ActuarialEngine(dummy_data, interest_rate=0.09)

    # 65 yaşında bir erkek için peşin ömür boyu anüite (ä_65) hesaplayalım
    annuity_value = engine.calculate_single_premium_annuity(
        age=65, gender="male", annuity_type="due"
    )

    print(f"--- AKTÜERYAL MOTOR TESTİ ---")
    print(f"Teknik Faiz Oranı: %{engine.i * 100}")
    print(f"65 yaşındaki erkek için peşin anüite değeri (ä_65): {annuity_value:.4f}")
    print(
        f"Yani her yıl 100.000 TL emekli maaşı ödemek için bugün gereken peşin rezerv: {100000 * annuity_value:,.2f} TL"
    )


# In[2]:


def calculate_advanced_annuity(N_series, D_series, age, annuity_type, deferral_period=0):
    """
    Mevcut komütasyon dizilerini kullanarak gelişmiş anüite tiplerini hesaplar.
    """
    # Yaş sınır kontrolleri
    if age not in D_series or D_series[age] == 0:
        return 0.0

    if annuity_type == "Peşin":
        return round(N_series[age] / D_series[age], 4)

    elif annuity_type == "Vadeli":
        target_age = age + 1
        if target_age in N_series:
            return round(N_series[target_age] / D_series[age], 4)
        return 0.0

    elif annuity_type == "Ertelemeli Peşin":
        target_age = age + deferral_period
        if target_age in N_series:
            return round(N_series[target_age] / D_series[age], 4)
        return 0.0

    return 0.0


# In[ ]:




