"""Value Objects do domínio: conceitos sem identidade, imutáveis, definidos por seus atributos."""
from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0
MPS_TO_KMH_FACTOR = 3.6


def mps_to_kmh(speed_ms: float) -> float:
    """Converte velocidade de m/s para km/h (1 m/s = 3.6 km/h)."""
    return speed_ms * MPS_TO_KMH_FACTOR


@dataclass(frozen=True)
class Coordinates:
    """Par latitude/longitude em WGS84, com validação de faixa e cálculo de distância."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"Latitude inválida: {self.latitude} (deve estar entre -90 e 90)")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"Longitude inválida: {self.longitude} (deve estar entre -180 e 180)")

    def distance_to(self, other: "Coordinates") -> float:
        """Distância em km via fórmula de Haversine."""
        lat1, lon1, lat2, lon2 = map(
            math.radians, [self.latitude, self.longitude, other.latitude, other.longitude]
        )
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return EARTH_RADIUS_KM * c
