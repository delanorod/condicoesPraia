from app.domain.value_objects import mps_to_kmh


class TestMpsToKmh:
    def test_converte_zero(self):
        assert mps_to_kmh(0.0) == 0.0

    def test_converte_valor_conhecido(self):
        # 10 m/s == 36 km/h (fator 3.6)
        assert mps_to_kmh(10.0) == 36.0

    def test_converte_valor_do_gfswave(self):
        assert round(mps_to_kmh(3.51), 2) == 12.64
