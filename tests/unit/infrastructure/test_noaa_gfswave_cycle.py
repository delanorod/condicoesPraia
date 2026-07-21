from datetime import datetime, timezone

import pytest

from app.infrastructure.noaa_gfswave_client import select_latest_available_cycle


class TestSelectLatestAvailableCycle:
    @pytest.mark.parametrize(
        "now,esperado",
        [
            # NOAA publica ~5h depois do horário do ciclo (00/06/12/18 UTC).
            (datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc), datetime(2026, 7, 13, 0, 0, tzinfo=timezone.utc)),
            (datetime(2026, 7, 13, 11, 30, tzinfo=timezone.utc), datetime(2026, 7, 13, 6, 0, tzinfo=timezone.utc)),
            (datetime(2026, 7, 13, 2, 0, tzinfo=timezone.utc), datetime(2026, 7, 12, 18, 0, tzinfo=timezone.utc)),
            (datetime(2026, 7, 13, 23, 59, tzinfo=timezone.utc), datetime(2026, 7, 13, 18, 0, tzinfo=timezone.utc)),
        ],
    )
    def test_seleciona_ciclo_mais_recente_ja_publicado(self, now, esperado):
        assert select_latest_available_cycle(now) == esperado
