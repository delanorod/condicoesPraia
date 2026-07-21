from datetime import datetime, timezone

import httpx
import pytest
import respx

from app.domain.value_objects import Coordinates
from app.infrastructure.open_meteo_client import (
    OPEN_METEO_MARINE_URL,
    OPEN_METEO_WEATHER_URL,
    OpenMeteoOceanDataSource,
    parse_open_meteo_wave,
    parse_open_meteo_wind,
)

# Formato real da Open-Meteo: bloco "current" com "time" em ISO 8601 local
# (sem timezone explícito) e um "current_units" descrevendo cada campo.
SAMPLE_MARINE_JSON = {
    "latitude": -22.99,
    "longitude": -43.19,
    "timezone": "America/Sao_Paulo",
    "current_units": {"time": "iso8601", "wave_height": "m", "wave_direction": "\u00b0", "wave_period": "s"},
    "current": {
        "time": "2026-07-13T12:00",
        "wave_height": 1.8,
        "wave_direction": 135.0,
        "wave_period": 8.0,
    },
}

SAMPLE_WEATHER_JSON = {
    "latitude": -22.99,
    "longitude": -43.19,
    "timezone": "America/Sao_Paulo",
    "current_units": {"time": "iso8601", "wind_speed_10m": "m/s", "wind_direction_10m": "\u00b0", "wind_gusts_10m": "m/s"},
    "current": {
        "time": "2026-07-13T12:00",
        "wind_speed_10m": 6.2,
        "wind_direction_10m": 90.0,
        "wind_gusts_10m": 8.1,
    },
}

SAMPLE_MARINE_JSON_NULLS = {
    **SAMPLE_MARINE_JSON,
    "current": {"time": "2026-07-13T12:00", "wave_height": None, "wave_direction": None, "wave_period": None},
}


class TestParseOpenMeteoWave:
    def test_extrai_leitura_de_onda_do_bloco_current(self):
        wave = parse_open_meteo_wave(SAMPLE_MARINE_JSON)
        assert wave.height_m == 1.8
        assert wave.period_s == 8.0
        assert wave.direction_deg == 135.0
        assert wave.observed_at == datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)

    def test_levanta_erro_quando_valores_sao_nulos(self):
        from app.infrastructure.open_meteo_client import OpenMeteoParseError
        with pytest.raises(OpenMeteoParseError, match="dados insuficientes"):
            parse_open_meteo_wave(SAMPLE_MARINE_JSON_NULLS)


class TestParseOpenMeteoWind:
    def test_extrai_leitura_de_vento_do_bloco_current(self):
        wind = parse_open_meteo_wind(SAMPLE_WEATHER_JSON)
        assert wind.speed_ms == 6.2
        assert wind.gust_ms == 8.1
        assert wind.direction_deg == 90.0


@pytest.mark.asyncio
class TestOpenMeteoOceanDataSource:
    async def test_busca_onda_via_marine_api(self):
        with respx.mock:
            respx.get(OPEN_METEO_MARINE_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARINE_JSON))
            respx.get(OPEN_METEO_WEATHER_URL).mock(return_value=httpx.Response(200, json=SAMPLE_WEATHER_JSON))
            async with httpx.AsyncClient() as client:
                source = OpenMeteoOceanDataSource(http_client=client)
                wave = await source.fetch_wave(Coordinates(latitude=-22.9868, longitude=-43.1897))

        assert wave.height_m == 1.8

    async def test_busca_vento_via_weather_api(self):
        with respx.mock:
            respx.get(OPEN_METEO_MARINE_URL).mock(return_value=httpx.Response(200, json=SAMPLE_MARINE_JSON))
            respx.get(OPEN_METEO_WEATHER_URL).mock(return_value=httpx.Response(200, json=SAMPLE_WEATHER_JSON))
            async with httpx.AsyncClient() as client:
                source = OpenMeteoOceanDataSource(http_client=client)
                wind = await source.fetch_wind(Coordinates(latitude=-22.9868, longitude=-43.1897))

        assert wind.speed_ms == 6.2
