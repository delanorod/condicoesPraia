from datetime import datetime, timedelta

from app.infrastructure.noaa_gfswave_client import candidate_cycles


class TestCandidateCycles:
    def test_gera_ciclos_em_ordem_decrescente_de_6_em_6_horas(self):
        now = datetime(2026, 7, 14, 17, 30)
        cycles = candidate_cycles(now, max_attempts=4)

        assert cycles == [
            datetime(2026, 7, 14, 12, 0),
            datetime(2026, 7, 14, 6, 0),
            datetime(2026, 7, 14, 0, 0),
            datetime(2026, 7, 13, 18, 0),
        ]

    def test_respeita_o_numero_maximo_de_tentativas(self):
        now = datetime(2026, 7, 14, 17, 30)
        assert len(candidate_cycles(now, max_attempts=2)) == 2
