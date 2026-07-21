from datetime import datetime, timezone

import pytest

from app.domain.entities import Beach, CoastalCondition, SeaState, WaveReading, WindReading
from app.domain.value_objects import Coordinates


def make_wave(height_m: float) -> WaveReading:
    return WaveReading(
        height_m=height_m,
        period_s=8.0,
        direction_deg=135.0,
        observed_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    )


def make_wind(speed_ms: float = 5.0) -> WindReading:
    return WindReading(
        speed_ms=speed_ms,
        gust_ms=speed_ms + 2.0,
        direction_deg=90.0,
        observed_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc),
    )


class TestWaveReading:
    def test_rejeita_altura_negativa(self):
        with pytest.raises(ValueError, match="altura"):
            make_wave(height_m=-1.0)

    def test_rejeita_periodo_nao_positivo(self):
        with pytest.raises(ValueError, match="período"):
            WaveReading(height_m=1.0, period_s=0, direction_deg=90.0,
                        observed_at=datetime.now(timezone.utc))


class TestWindReading:
    def test_rejeita_velocidade_negativa(self):
        with pytest.raises(ValueError, match="velocidade"):
            make_wind(speed_ms=-1.0)


class TestSeaStateClassification:
    """Escala Douglas simplificada para praias oceânicas (não confundir com escala Beaufort de vento)."""

    @pytest.mark.parametrize(
        "height_m,estado_esperado",
        [
            (0.0, SeaState.CALMO),
            (0.05, SeaState.CALMO),
            (0.10, SeaState.QUASE_CALMO),
            (0.49, SeaState.QUASE_CALMO),
            (0.50, SeaState.LEVE),
            (1.24, SeaState.LEVE),
            (1.25, SeaState.MODERADO),
            (2.49, SeaState.MODERADO),
            (2.50, SeaState.AGITADO),
            (4.0, SeaState.AGITADO),
            (4.01, SeaState.MUITO_AGITADO),
            (6.0, SeaState.MUITO_AGITADO),
            (6.01, SeaState.ALTO),
        ],
    )
    def test_classifica_estado_do_mar_por_altura_de_onda(self, height_m, estado_esperado):
        wave = make_wave(height_m=height_m)
        assert wave.classify_sea_state() == estado_esperado


class TestCoastalCondition:
    def test_agrega_praia_vento_e_onda_com_indicador_de_mar_agitado(self):
        beach = Beach(
            id="copacabana",
            name="Copacabana",
            coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897),
        )
        condition = CoastalCondition(beach=beach, wind=make_wind(), wave=make_wave(height_m=3.0))

        assert condition.sea_state == SeaState.AGITADO
        assert condition.is_rough() is True

    def test_mar_calmo_nao_e_considerado_agitado(self):
        beach = Beach(
            id="copacabana",
            name="Copacabana",
            coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897),
        )
        condition = CoastalCondition(beach=beach, wind=make_wind(), wave=make_wave(height_m=0.3))

        assert condition.is_rough() is False
