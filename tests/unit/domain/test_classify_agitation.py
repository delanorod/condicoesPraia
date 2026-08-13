import pytest

from app.domain.scoring import classify_agitation


class TestClassifyAgitation:
    @pytest.mark.parametrize("altura_m,esperado", [
        (0.0, "Fraco"),
        (0.49, "Fraco"),
        (0.5, "Moderado"),
        (1.24, "Moderado"),
        (1.25, "Forte"),
        (2.49, "Forte"),
        (2.5, "Muito Forte"),
        (5.0, "Muito Forte"),
    ])
    def test_classifica_agitacao_pela_altura_da_onda(self, altura_m, esperado):
        assert classify_agitation(altura_m) == esperado
