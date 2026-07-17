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