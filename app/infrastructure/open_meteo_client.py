"""Adapter para a Open-Meteo: Marine API (ondas) + Weather API (vento).

Ao contrário do NOAA NDBC, a Open-Meteo não usa boias físicas — é um modelo
de previsão (dados de reanálise/forecast), então cobre qualquer coordenada
do planeta, incluindo o litoral do Rio de Janeiro. Não requer chave de API
para uso não comercial. Docs: https://open-meteo.com/en/docs/marine-weather-api
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.domain.entities import WaveReading, WindReading
from app.domain.repositories import OceanDataSource
from app.domain.value_objects import Coordinates

OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoParseError(ValueError):
    """Resposta da Open-Meteo vazia, malformada ou com campos essenciais nulos."""


def _parse_local_time(iso_local: str) -> datetime:
    # A Open-Meteo retorna hora local sem timezone quando &timezone=auto;
    # aqui pedimos explicitamente timezone=UTC na query, então isso é UTC.
    from datetime import timezone as _tz
    return datetime.fromisoformat(iso_local).replace(tzinfo=_tz.utc)


def parse_open_meteo_wave(payload: dict) -> WaveReading:
    current = payload.get("current") or {}
    height, period, direction = current.get("wave_height"), current.get("wave_period"), current.get("wave_direction")
    if height is None or period is None or direction is None:
        raise OpenMeteoParseError("dados insuficientes: campos de onda nulos na resposta")
    return WaveReading(
        height_m=float(height),
        period_s=float(period),
        direction_deg=float(direction),
        observed_at=_parse_local_time(current["time"]),
    )


def parse_open_meteo_wind(payload: dict) -> WindReading:
    current = payload.get("current") or {}
    speed, gust, direction = (
        current.get("wind_speed_10m"), current.get("wind_gusts_10m"), current.get("wind_direction_10m"),
    )
    if speed is None or gust is None or direction is None:
        raise OpenMeteoParseError("dados insuficientes: campos de vento nulos na resposta")
    return WindReading(
        speed_ms=float(speed),
        gust_ms=float(gust),
        direction_deg=float(direction),
        observed_at=_parse_local_time(current["time"]),
    )


class OpenMeteoOceanDataSource(OceanDataSource):
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def fetch_wave(self, coordinates: Coordinates) -> WaveReading:
        response = await self._http_client.get(OPEN_METEO_MARINE_URL, params={
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "current": "wave_height,wave_direction,wave_period",
            "timezone": "UTC",
        })
        response.raise_for_status()
        return parse_open_meteo_wave(response.json())

    async def fetch_wind(self, coordinates: Coordinates) -> WindReading:
        response = await self._http_client.get(OPEN_METEO_WEATHER_URL, params={
            "latitude": coordinates.latitude,
            "longitude": coordinates.longitude,
            "current": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "wind_speed_unit": "ms",
            "timezone": "UTC",
        })
        response.raise_for_status()
        return parse_open_meteo_wind(response.json())
