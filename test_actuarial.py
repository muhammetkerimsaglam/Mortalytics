import pytest
from actuarial_engine import calculate_advanced_annuity

def test_annuity_logic():
    # Test için basit ve kontrolü kolay sahte N_x ve D_x komütasyon serileri oluşturalım
    # Yaşlar: 65, 66, 67
    D_series = {65: 100.0, 66: 100.0, 67: 100.0}
    N_series = {
        67: 100.0,          # N_67 = D_67 = 100
        66: 100.0 + 100.0,  # N_66 = D_66 + D_67 = 200
        65: 200.0 + 100.0   # N_65 = D_65 + D_66 + D_67 = 300
    }
    
    # 1. Peşin test: N_65 / D_65 = 300 / 100 = 3.0
    pesin = calculate_advanced_annuity(N_series, D_series, age=65, annuity_type="Peşin")
    assert pesin == 3.0
    
    # 2. Vadeli test: N_66 / D_65 = 200 / 100 = 2.0
    vadeli = calculate_advanced_annuity(N_series, D_series, age=65, annuity_type="Vadeli")
    assert vadeli == 2.0
    
    # 3. Ertelemeli Peşin test (2 yıl ertelemeli): N_67 / D_65 = 100 / 100 = 1.0
    ertelemeli = calculate_advanced_annuity(N_series, D_series, age=65, annuity_type="Ertelemeli Peşin", deferral_period=2)
    assert ertelemeli == 1.0