"""
math_engine.py
================
Mortalytics projesinin TEK GERÇEK KAYNAĞI (single source of truth).

Bu dosya, projenin tüm aktüeryal hesaplama mantığını (yaşam tablosu üretimi,
komütasyon fonksiyonları, anüite hesaplamaları, Monte Carlo simülasyonu) içerir.

Diğer dosyalar (app.py, actuarial_engine.py, trh2010_generator.py,
main_test.py) bu modülü İMPORT EDER; hiçbiri kendi başına kod
tekrarlamaz. Bir hesaplama mantığını değiştirmeniz gerekirse, SADECE bu
dosyayı düzenlemeniz yeterlidir — diğer tüm dosyalar otomatik olarak
güncel mantığı kullanır.

Bu modül BİLİNÇLİ OLARAK Streamlit'e bağımlı değildir (import streamlit yok).
Sebep: pytest gibi test araçlarıyla, arayüz çalıştırılmadan (sidebar, slider
vb. oluşturulmadan) doğrudan test edilebilmesi. Streamlit'e özel önbellekleme
(@st.cache_data) çağıran sarmalayıcılar app.py içinde tutulur.

ÖNEMLİ VERİ NOTU:
generate_trh2010_data() TSB/SBM tarafından yayınlanan RESMİ TRH-2010 tablosunu
kullanmaz. lx değerleri parametrik bir güç fonksiyonuyla üretilmiş SENTETİK/
YAKLAŞIK bir tablodur. Gerçek aktüeryal, sigortacılık veya hukuki (tazminat
vb.) hesaplamalarda kullanılmamalıdır. Bu araç yalnızca eğitim/demo amaçlıdır.
"""

import numpy as np
import pandas as pd


# ==============================================================================
# 1. TRH-2010 (SENTETİK/YAKLAŞIK) VERİ ÜRETİCİSİ
# ==============================================================================
def generate_trh2010_data() -> pd.DataFrame:
    """
    TRH-2010 yaşam tablosunun genel eğilimini (kadınların erkeklerden daha
    uzun yaşaması, yaşlılıkta hızlanan ölüm oranları vb.) yansıtan SENTETİK/
    YAKLAŞIK bir yaşam tablosu üretir.

    ÖNEMLİ: Bu fonksiyon TSB/SBM tarafından yayınlanan RESMİ TRH-2010 tablosunu
    kullanmaz. lx değerleri parametrik bir güç fonksiyonuyla üretilmiştir ve
    gerçek qx/lx değerlerinden sapabilir. Gerçek aktüeryal/hukuki hesaplamalar
    (tazminat, rezerv, prim vb.) için resmi TRH-2010 tablosu kullanılmalıdır.
    Bu araç yalnızca eğitim/demo amaçlıdır.

    Başlangıç kohortu (l0), her iki cinsiyet için de 100.000 kişi olarak
    kabul edilmiştir.
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
    """
    Desteklenen annuity_type değerleri:
      - "due"                 : Ömür boyu, dönem başı (peşin)   -> äx = Nx / Dx
      - "immediate"            : Ömür boyu, dönem sonu (adi)     -> ax = N(x+1) / Dx
      - "deferred_due"         : n yıl ertelemeli, dönem başı    -> n|äx = N(x+n) / Dx
      - "deferred_immediate"   : n yıl ertelemeli, dönem sonu    -> n|ax = N(x+n+1) / Dx
      - "term_due"             : n yıl vadeli, dönem başı        -> n_äx = (Nx - N(x+n)) / Dx
      - "term_immediate"       : n yıl vadeli, dönem sonu        -> n_ax = (N(x+1) - N(x+n+1)) / Dx

    Matematiksel invariant (test edilir): term_due + deferred_due (aynı n
    için) = due (ömür boyu). Yani bir anüiteyi n yıl vadeli ve n yıl sonrası
    ertelemeli olarak ikiye bölmek, tam ömür boyu anüiteye eşittir.
    """

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

    def _lookup(self, df_comm: pd.DataFrame, age: int):
        """Yardımcı: verilen yaş için (Dx, Nx) çiftini döndürür, yoksa (None, None)."""
        row = df_comm[df_comm["Age"] == age]
        if row.empty:
            return None, None
        return row["Dx"].values[0], row["Nx"].values[0]

    def calculate_single_premium_annuity(
        self,
        age: int,
        gender: str = "male",
        annuity_type: str = "due",
        deferral_period: int = 0,
        term_years: int = 0,
    ):
        """
        Tek primli anüite değerini hesaplar. Yukarıdaki class docstring'inde
        listelenen 6 annuity_type değerinden birini kabul eder.

        :param age: Bireyin yaşı (x)
        :param gender: 'male' (erkek) veya 'female' (kadın)
        :param annuity_type: "due" | "immediate" | "deferred_due" |
                              "deferred_immediate" | "term_due" | "term_immediate"
        :param deferral_period: "deferred_*" tipleri için erteleme yılı (n)
        :param term_years: "term_*" tipleri için vade yılı (n)
        """
        df_comm = self.calculate_commutation_functions(gender)
        Dx, Nx = self._lookup(df_comm, age)
        if Dx is None:
            raise ValueError(f"Seçilen yaş ({age}) yaşam tablosunda bulunamadı.")
        if Dx == 0:
            return 0.0

        if annuity_type == "due":
            return Nx / Dx

        elif annuity_type == "immediate":
            _, Nx_plus_1 = self._lookup(df_comm, age + 1)
            return (Nx_plus_1 / Dx) if Nx_plus_1 is not None else 0.0

        elif annuity_type == "deferred_due":
            if deferral_period < 0:
                raise ValueError("deferral_period negatif olamaz")
            _, N_target = self._lookup(df_comm, age + deferral_period)
            return (N_target / Dx) if N_target is not None else 0.0

        elif annuity_type == "deferred_immediate":
            if deferral_period < 0:
                raise ValueError("deferral_period negatif olamaz")
            _, N_target = self._lookup(df_comm, age + deferral_period + 1)
            return (N_target / Dx) if N_target is not None else 0.0

        elif annuity_type == "term_due":
            if term_years < 0:
                raise ValueError("term_years negatif olamaz")
            if term_years == 0:
                return 0.0
            _, N_end = self._lookup(df_comm, age + term_years)
            N_end = N_end if N_end is not None else 0.0
            return (Nx - N_end) / Dx

        elif annuity_type == "term_immediate":
            if term_years < 0:
                raise ValueError("term_years negatif olamaz")
            if term_years == 0:
                return 0.0
            _, N_start = self._lookup(df_comm, age + 1)
            _, N_end = self._lookup(df_comm, age + term_years + 1)
            N_start = N_start if N_start is not None else 0.0
            N_end = N_end if N_end is not None else 0.0
            return (N_start - N_end) / Dx

        else:
            raise ValueError(f"Bilinmeyen annuity_type: {annuity_type}")


# ==============================================================================
# 3. MONTE CARLO KOHORT SİMÜLATÖRÜ
# ==============================================================================
class CohortSimulator:
    def __init__(self, mortality_df: pd.DataFrame):
        """
        Bireysel bazda yaşam ve ölüm süreçlerini simüle eden sınıf.
        """
        self.df = mortality_df

    def run_simulation(self, start_age: int, gender: str, cohort_size: int = 10000, seed: int = 42):
        """
        Her bir birey için yaşam/ölüm durumunu yıl yıl simüle eder.

        :param start_age: Simülasyonun başlayacağı yaş (emeklilik yaşı)
        :param gender: 'male' (erkek) veya 'female' (kadın)
        :param cohort_size: Başlangıçtaki toplam simüle edilecek kişi sayısı
        :param seed: Rastgelelik için sabit tohum (tekrarlanabilir sonuçlar için)
        """
        # Sabit seed: aynı parametrelerle her çalıştırmada aynı (tekrarlanabilir) sonuç üretir
        np.random.seed(seed)

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


# ==============================================================================
# 4. REZERV YETERLİLİĞİ DAĞILIMI (Monte Carlo Risk Analizi)
# ==============================================================================
def calculate_realized_cost(
    sim_results: pd.DataFrame,
    annuity_pay: float,
    interest_rate: float,
    annuity_type: str = "due",
    deferral_period: int = 0,
    term_years: int = 0,
) -> float:
    """
    Tek bir simülasyon sonucundan (yıl yıl hayatta kalan sayısı), seçilen
    anüite tipine göre GERÇEKLEŞEN toplam iskonto edilmiş ödeme tutarını
    hesaplar.

    Mantık: Her yıl, o yıl hayatta olan kişi sayısı kadar ödeme yapılır
    (annuity_pay × hayatta kalan sayısı), bu tutar o yılın iskonto
    faktörüyle (v^t) bugüne indirgenir ve toplanır. Hangi yıllarda ödeme
    yapılacağı annuity_type'a göre değişir (örn. "term_due" sadece ilk
    n yıl öder, "deferred_due" ilk n yıl ödemez).

    Bu değer, çok sayıda simülasyon üzerinden tekrarlandığında (bkz.
    run_reserve_distribution), ortalaması deterministik rezerv formülüne
    (calculate_single_premium_annuity ile hesaplanan) yakınsar — büyük
    sayılar kanununun görsel bir kanıtı.
    """
    v = 1 / (1 + interest_rate)
    t_idx = sim_results["Year"].values
    survivors = sim_results["Survivors"].values
    num_years = len(t_idx)

    if annuity_type == "due":
        mask = t_idx >= 0
    elif annuity_type == "immediate":
        mask = t_idx >= 1
    elif annuity_type == "deferred_due":
        mask = t_idx >= deferral_period
    elif annuity_type == "deferred_immediate":
        mask = t_idx >= (deferral_period + 1)
    elif annuity_type == "term_due":
        mask = t_idx < term_years
    elif annuity_type == "term_immediate":
        mask = (t_idx >= 1) & (t_idx <= term_years)
    else:
        raise ValueError(f"Bilinmeyen annuity_type: {annuity_type}")

    discount = v ** t_idx.astype(float)
    return float(np.sum(survivors[mask] * annuity_pay * discount[mask]))


def run_reserve_distribution(
    mortality_df: pd.DataFrame,
    start_age: int,
    gender: str,
    cohort_size: int,
    interest_rate: float,
    annuity_pay: float,
    annuity_type: str = "due",
    deferral_period: int = 0,
    term_years: int = 0,
    n_simulations: int = 200,
    base_seed: int = 1000,
) -> np.ndarray:
    """
    Aynı kohort parametreleriyle Monte Carlo simülasyonunu n_simulations
    kez tekrarlar (her seferinde farklı bir seed ile) ve her tekrarda
    gerçekleşen toplam ödeme maliyetini toplar. Dönen dizi, bu maliyetlerin
    dağılımını (histogram için) temsil eder.

    Not: Her tekrar farklı bir seed (base_seed + i) kullanır — bu yüzden
    run_simulation() içindeki varsayılan sabit seed burada override edilir.
    """
    if n_simulations < 1:
        raise ValueError("n_simulations en az 1 olmalı")

    simulator = CohortSimulator(mortality_df)
    costs = np.empty(n_simulations)

    for i in range(n_simulations):
        sim_results = simulator.run_simulation(
            start_age, gender, cohort_size, seed=base_seed + i
        )
        costs[i] = calculate_realized_cost(
            sim_results, annuity_pay, interest_rate,
            annuity_type, deferral_period, term_years,
        )

    return costs