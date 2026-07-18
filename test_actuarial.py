"""
test_actuarial.py
====================
math_engine.ActuarialEngine için pytest testleri.

ÖNEMLİ: Bu testler artık `actuarial_engine.py` (sadece bir sarmalayıcı)
üzerinden ama esasen `math_engine.py` içindeki GERÇEK, app.py tarafından
KULLANILAN kodu test ediyor. Önceki versiyonda testler, uygulamada hiç
kullanılmayan, class'a bağlı bile olmayan ayrı bir fonksiyonu (dead code)
test ediyordu — bu artık düzeltildi.

Test felsefesi: TRH-2010 tablosu sentetik olduğu için "gerçek dünya" bir
referans değere karşı test edemeyiz. Bunun yerine, HANGİ TABLO KULLANILIRSA
KULLANILSIN her zaman doğru olması gereken AKTÜERYAL MATEMATİK
ÖZELLİKLERİNİ (invariant) test ediyoruz.
"""

import numpy as np
import pandas as pd
import pytest

from actuarial_engine import ActuarialEngine


@pytest.fixture(scope="module")
def mortality_df():
    """
    Monte Carlo / rezerv dağılımı testleri için gerçekçi (0-100 yaş aralığında,
    qx/lx içeren) tam bir sentetik yaşam tablosu. simple_engine fixture'ındaki
    4 yaşlık minik tablo, run_simulation()'ın 0-100 yaş aralığına ihtiyaç
    duyan iç mantığı için yetersiz kalır.
    """
    from math_engine import generate_trh2010_data
    return generate_trh2010_data()


@pytest.fixture
def simple_engine():
    """
    Basit, elle kontrol edilebilir bir yaşam tablosuyla motor oluşturur.
    Yaşlar: 65, 66, 67, 68 — sabit Dx=100 üretecek şekilde tasarlanmıştır
    (i=0 kullanarak v=1 olur, böylece Dx = lx olur, hesabı elle doğrulamak kolaylaşır).
    """
    ages = np.array([65, 66, 67, 68])
    lx = np.array([100.0, 100.0, 100.0, 100.0])  # v=1 olduğunda Dx = lx = 100 sabit
    df = pd.DataFrame({"Age": ages, "lx_male": lx, "lx_female": lx})
    return ActuarialEngine(df, interest_rate=0.0)  # i=0 -> v=1, elle doğrulama kolay


class TestBasicAnnuityTypes:

    def test_due_annuity(self, simple_engine):
        """
        äx = Nx/Dx. Dx=100 sabit olduğundan Nx(65) = 100*4 = 400 (65,66,67,68).
        ä_65 = 400/100 = 4.0
        """
        result = simple_engine.calculate_single_premium_annuity(65, "male", "due")
        assert result == pytest.approx(4.0)

    def test_immediate_annuity(self, simple_engine):
        """
        ax = N(x+1)/Dx. N_66 = 100*3 = 300 (66,67,68). a_65 = 300/100 = 3.0
        """
        result = simple_engine.calculate_single_premium_annuity(65, "male", "immediate")
        assert result == pytest.approx(3.0)

    def test_due_equals_one_plus_immediate(self, simple_engine):
        """Temel kimlik: äx = 1 + ax."""
        due = simple_engine.calculate_single_premium_annuity(65, "male", "due")
        immediate = simple_engine.calculate_single_premium_annuity(65, "male", "immediate")
        assert due == pytest.approx(1 + immediate)


class TestDeferredAnnuity:

    def test_deferred_due(self, simple_engine):
        """
        n|äx = N(x+n)/Dx. 2 yıl ertelemeli: N_67 = 100*2 = 200. n|ä_65 = 200/100 = 2.0
        """
        result = simple_engine.calculate_single_premium_annuity(
            65, "male", "deferred_due", deferral_period=2
        )
        assert result == pytest.approx(2.0)

    def test_zero_deferral_equals_due(self, simple_engine):
        """0 yıl erteleme, normal äx ile aynı olmalı."""
        due = simple_engine.calculate_single_premium_annuity(65, "male", "due")
        deferred_zero = simple_engine.calculate_single_premium_annuity(
            65, "male", "deferred_due", deferral_period=0
        )
        assert deferred_zero == pytest.approx(due)

    def test_negative_deferral_raises(self, simple_engine):
        with pytest.raises(ValueError):
            simple_engine.calculate_single_premium_annuity(
                65, "male", "deferred_due", deferral_period=-1
            )


class TestTermAnnuity:

    def test_term_due(self, simple_engine):
        """
        n_äx = (Nx - N(x+n))/Dx. 2 yıl vadeli: (400 - 200)/100 = 2.0
        """
        result = simple_engine.calculate_single_premium_annuity(
            65, "male", "term_due", term_years=2
        )
        assert result == pytest.approx(2.0)

    def test_term_zero_years_returns_zero(self, simple_engine):
        result = simple_engine.calculate_single_premium_annuity(
            65, "male", "term_due", term_years=0
        )
        assert result == 0.0

    def test_negative_term_raises(self, simple_engine):
        with pytest.raises(ValueError):
            simple_engine.calculate_single_premium_annuity(
                65, "male", "term_due", term_years=-1
            )


class TestTermPlusDeferredInvariant:
    """
    KİLİT MATEMATİKSEL DOĞRULAMA: Bir ömür boyu anüiteyi n yıl vadeli +
    n yıl sonrasının ertelemeli anüitesi olarak ikiye bölmek, orijinal
    ömür boyu anüiteye eşit olmalıdır. Bu, tablo ne olursa olsun (sentetik
    ya da gerçek) HER ZAMAN doğru olması gereken bir matematik kimliğidir.
    """

    def test_term_plus_deferred_equals_whole_life_due(self, simple_engine):
        whole_life = simple_engine.calculate_single_premium_annuity(65, "male", "due")
        term = simple_engine.calculate_single_premium_annuity(65, "male", "term_due", term_years=2)
        deferred = simple_engine.calculate_single_premium_annuity(65, "male", "deferred_due", deferral_period=2)
        assert term + deferred == pytest.approx(whole_life)

    def test_term_plus_deferred_equals_whole_life_immediate(self, simple_engine):
        whole_life = simple_engine.calculate_single_premium_annuity(65, "male", "immediate")
        term = simple_engine.calculate_single_premium_annuity(65, "male", "term_immediate", term_years=2)
        deferred = simple_engine.calculate_single_premium_annuity(65, "male", "deferred_immediate", deferral_period=2)
        assert term + deferred == pytest.approx(whole_life)


class TestErrorHandling:

    def test_unknown_annuity_type_raises(self, simple_engine):
        with pytest.raises(ValueError):
            simple_engine.calculate_single_premium_annuity(65, "male", "gecersiz_tip")

    def test_unknown_age_raises(self, simple_engine):
        with pytest.raises(ValueError):
            simple_engine.calculate_single_premium_annuity(999, "male", "due")


class TestReserveDistribution:
    """
    run_reserve_distribution() / calculate_realized_cost() için testler.
    Kilit beklenti: Monte Carlo ortalaması, deterministik (Nx/Dx tabanlı)
    rezerv formülüne yakınsamalı (büyük sayılar kanunu).
    """

    def test_mc_average_converges_to_deterministic_reserve(self, mortality_df):
        from math_engine import run_reserve_distribution

        engine = ActuarialEngine(mortality_df, interest_rate=0.09)
        annuity_val = engine.calculate_single_premium_annuity(65, "male", "due")
        cohort_size = 5000
        annuity_pay = 100000
        deterministic_reserve = cohort_size * annuity_pay * annuity_val

        costs = run_reserve_distribution(
            mortality_df, 65, "male", cohort_size, 0.09, annuity_pay,
            "due", n_simulations=150,
        )
        # %2 tolerans içinde yakınsamalı (büyük kohort + yeterli tekrar sayısı)
        assert costs.mean() == pytest.approx(deterministic_reserve, rel=0.02)

    def test_variability_decreases_with_larger_cohort(self, mortality_df):
        """Kohort büyüdükçe değişim katsayısı (CV) küçülmeli (havuzlama etkisi)."""
        from math_engine import run_reserve_distribution

        small_costs = run_reserve_distribution(
            mortality_df, 65, "male", 200, 0.09, 100000, "due", n_simulations=100
        )
        large_costs = run_reserve_distribution(
            mortality_df, 65, "male", 5000, 0.09, 100000, "due", n_simulations=100
        )
        cv_small = small_costs.std() / small_costs.mean()
        cv_large = large_costs.std() / large_costs.mean()
        assert cv_large < cv_small

    def test_n_simulations_returns_correct_length(self, mortality_df):
        from math_engine import run_reserve_distribution

        costs = run_reserve_distribution(
            mortality_df, 65, "male", 500, 0.09, 100000, "due", n_simulations=37
        )
        assert len(costs) == 37

    def test_invalid_n_simulations_raises(self, mortality_df):
        from math_engine import run_reserve_distribution

        with pytest.raises(ValueError):
            run_reserve_distribution(
                mortality_df, 65, "male", 500, 0.09, 100000, "due", n_simulations=0
            )


class TestStochasticInterestRate:
    """
    CIR (Cox-Ingersoll-Ross) stokastik faiz modeli için testler.

    Kilit tutarlılık kontrolü: sigma=0 (oynaklık yok) verildiğinde, faiz hiç
    dalgalanmaz ve stokastik anüite sonucu, deterministik formülle (Nx/Dx)
    hesaplanan sonuçla BİREBİR örtüşmelidir. Bu, iki farklı hesaplama
    yolunun (deterministik vs. stokastik) matematiksel olarak tutarlı
    olduğunu kanıtlar.
    """

    def test_sigma_zero_matches_deterministic(self, mortality_df):
        from math_engine import calculate_stochastic_annuity

        engine = ActuarialEngine(mortality_df, interest_rate=0.09)
        det_val = engine.calculate_single_premium_annuity(65, "male", "due")

        stoch_vals = calculate_stochastic_annuity(
            mortality_df, 65, "male", "due", a=0.2, b=0.09, sigma=0.0, n_paths=50
        )
        assert stoch_vals.mean() == pytest.approx(det_val, abs=1e-9)
        assert stoch_vals.std() == pytest.approx(0.0, abs=1e-9)

    def test_no_negative_rates_ever_generated(self):
        from math_engine import simulate_cir_rate_paths

        # Yüksek oynaklık ve uzun vade ile bile negatif faiz üretilmemeli
        paths = simulate_cir_rate_paths(
            r0=0.09, a=0.2, b=0.09, sigma=0.08, n_years=50, n_paths=2000, seed=7
        )
        assert paths.min() >= 0.0

    def test_n_paths_returns_correct_length(self, mortality_df):
        from math_engine import calculate_stochastic_annuity

        vals = calculate_stochastic_annuity(
            mortality_df, 65, "male", "due", a=0.2, b=0.09, sigma=0.02, n_paths=73
        )
        assert len(vals) == 73

    def test_invalid_mean_reversion_speed_raises(self):
        from math_engine import simulate_cir_rate_paths

        with pytest.raises(ValueError):
            simulate_cir_rate_paths(r0=0.09, a=0.0, b=0.09, sigma=0.02, n_years=10, n_paths=10)

    def test_negative_sigma_raises(self):
        from math_engine import simulate_cir_rate_paths

        with pytest.raises(ValueError):
            simulate_cir_rate_paths(r0=0.09, a=0.2, b=0.09, sigma=-0.01, n_years=10, n_paths=10)

    def test_stochastic_mean_close_to_deterministic_with_realistic_sigma(self, mortality_df):
        """Gerçekçi (küçük) oynaklıkla, stokastik ortalama deterministik değerden çok uzaklaşmamalı."""
        from math_engine import calculate_stochastic_annuity

        engine = ActuarialEngine(mortality_df, interest_rate=0.09)
        det_val = engine.calculate_single_premium_annuity(65, "male", "due")

        stoch_vals = calculate_stochastic_annuity(
            mortality_df, 65, "male", "due", a=0.2, b=0.09, sigma=0.02, n_paths=1000, seed=99
        )
        assert stoch_vals.mean() == pytest.approx(det_val, rel=0.05)