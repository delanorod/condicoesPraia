"""Entidades e agregados do domínio de condições costeiras."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.domain.value_objects import Coordinates


class SeaState(str, Enum):
    """Escala Douglas simplificada, por altura significativa de onda (m)."""

    CALMO = "calmo"                # 0 - 0.10
    QUASE_CALMO = "quase_calmo"    # 0.10 - 0.50
    LEVE = "leve"                  # 0.50 - 1.25
    MODERADO = "moderado"          # 1.25 - 2.50
    AGITADO = "agitado"            # 2.50 - 4.00
    MUITO_AGITADO = "muito_agitado"  # 4.00 - 6.00
    ALTO = "alto"                  # > 6.00


# Cada faixa é [lower, upper), exceto AGITADO e MUITO_AGITADO que fecham no
# limite superior (convenção da escala Douglas: 4.00m ainda é "agitado").
_SEA_STATE_THRESHOLDS: tuple[tuple[float, SeaState], ...] = (
    (0.10, SeaState.CALMO),          # h <  0.10
    (0.50, SeaState.QUASE_CALMO),    # h <  0.50
    (1.25, SeaState.LEVE),           # h <  1.25
    (2.50, SeaState.MODERADO),       # h <  2.50
    (4.00, SeaState.AGITADO),        # h <= 4.00
    (6.00, SeaState.MUITO_AGITADO),  # h <= 6.00
)
_STRICT_LESS_THAN_COUNT = 4  # as primeiras N faixas usam '<'; as demais usam '<='

# Estados considerados "mar agitado" para fins de alerta ao usuário.
ROUGH_SEA_STATES = frozenset({SeaState.AGITADO, SeaState.MUITO_AGITADO, SeaState.ALTO})


@dataclass(frozen=True)
class WaveReading:
    height_m: float
    period_s: float
    direction_deg: float
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.height_m < 0:
            raise ValueError(f"altura de onda inválida: {self.height_m}")
        if self.period_s <= 0:
            raise ValueError(f"período de onda inválido: {self.period_s}")

    def classify_sea_state(self) -> SeaState:
        for index, (upper_bound, state) in enumerate(_SEA_STATE_THRESHOLDS):
            if index < _STRICT_LESS_THAN_COUNT:
                if self.height_m < upper_bound:
                    return state
            elif self.height_m <= upper_bound:
                return state
        return SeaState.ALTO


@dataclass(frozen=True)
class WindReading:
    speed_ms: float
    gust_ms: float
    direction_deg: float
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.speed_ms < 0:
            raise ValueError(f"velocidade de vento inválida: {self.speed_ms}")


@dataclass(frozen=True)
class Beach:
    id: str
    name: str
    coordinates: Coordinates
    municipality: str = "Rio de Janeiro"
    neighborhood: str = ""
    region: str = ""
    characteristics: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoastalCondition:
    """Agregado raiz: a condição costeira observada de uma praia em um instante."""

    beach: Beach
    wind: WindReading
    wave: WaveReading

    @property
    def sea_state(self) -> SeaState:
        return self.wave.classify_sea_state()

    def is_rough(self) -> bool:
        return self.sea_state in ROUGH_SEA_STATES
