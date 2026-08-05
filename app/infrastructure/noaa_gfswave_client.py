"""Adapter para o NOAA GFS-Wave (WAVEWATCH III) via NOMADS.

Dados de domínio público do governo dos EUA (17 U.S.C. § 105), sem qualquer
restrição de uso comercial — ao contrário das fontes anteriores testadas
(Open-Meteo: não comercial; PacIOOS: cortesia acadêmica ambígua).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.domain.entities import WaveReading, WindReading
from app.domain.repositories import OceanDataSource
from app.domain.value_objects import Coordinates

NOMADS_GFSWAVE_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfswave.pl"
CYCLE_HOURS = (0, 6, 12, 18)
PUBLISH_DELAY_HOURS = 5
GRID_STEP_DEG = 0.25
SEARCH_BOX_DEG = 1.5
# Média diária de vento, pra ficar comparável com a metodologia do
# Open-Meteo (extrator_ondasZSul.py::buscar_vento faz média das 24 horas
# do dia). O GFS-Wave só publica de 3 em 3 horas, então usamos 8 pontos
# (00, 03, 06, ..., 21) cobrindo o dia inteiro a partir do ciclo escolhido.
DAILY_AVERAGE_FORECAST_HOURS = (0, 3, 6, 9, 12, 15, 18, 21)


def select_latest_available_cycle(now_utc: datetime, publish_delay_hours: int = PUBLISH_DELAY_HOURS) -> datetime:
    cycle_hour = (now_utc.hour // 6) * 6
    cycle = now_utc.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)
    while now_utc < cycle + timedelta(hours=publish_delay_hours):
        cycle -= timedelta(hours=6)
    return cycle


def candidate_cycles(now_utc: datetime, max_attempts: int = 4) -> list[datetime]:
    first = select_latest_available_cycle(now_utc)
    return [first - timedelta(hours=6 * i) for i in range(max_attempts)]


def build_gfswave_grib_filter_url(cycle: datetime, coordinates: Coordinates, forecast_hour: int = 0) -> str:
    date_str = cycle.strftime("%Y%m%d")
    cycle_str = f"{cycle.hour:02d}"
    forecast_str = f"{forecast_hour:03d}"

    left = coordinates.longitude % 360 - SEARCH_BOX_DEG
    right = coordinates.longitude % 360 + SEARCH_BOX_DEG
    top = coordinates.latitude + SEARCH_BOX_DEG
    bottom = coordinates.latitude - SEARCH_BOX_DEG

    params = {
        "file": f"gfswave.t{cycle_str}z.global.0p25.f{forecast_str}.grib2",
        "var_HTSGW": "on",
        "var_DIRPW": "on",
        "var_PERPW": "on",
        "var_WIND": "on",
        "var_WDIR": "on",
        "subregion": "",
        "leftlon": str(left),
        "rightlon": str(right),
        "toplat": str(top),
        "bottomlat": str(bottom),
        "dir": f"/gfs.{date_str}/{cycle_str}/wave/gridded",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{NOMADS_GFSWAVE_FILTER_URL}?{query}"


class GfsWaveParseError(ValueError):
    pass


def parse_gfswave_grib2(raw_bytes: bytes, coordinates: Coordinates) -> dict[str, float]:
    if not raw_bytes.startswith(b"GRIB"):
        raise GfsWaveParseError("resposta do NOMADS não é um arquivo GRIB2 válido")

    import os
    import tempfile
    import time

    import eccodes

    values: dict[str, float] = {}
    fd, tmp_path = tempfile.mkstemp(suffix=".grib2")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw_bytes)

        last_error: OSError | None = None
        for attempt in range(5):
            try:
                with open(tmp_path, "rb") as f:
                    while True:
                        msg_id = eccodes.codes_grib_new_from_file(f)
                        if msg_id is None:
                            break
                        try:
                            short_name = eccodes.codes_get(msg_id, "shortName")
                            try:
                                missing_value = eccodes.codes_get(msg_id, "missingValue")
                            except Exception:
                                missing_value = None

                            candidates = eccodes.codes_grib_find_nearest(
                                msg_id, coordinates.latitude, coordinates.longitude, npoints=4
                            )
                            for candidate in candidates:
                                value = candidate.value
                                if missing_value is not None and value == missing_value:
                                    continue
                                if value in (9999.0, 9999):
                                    continue
                                values[short_name] = value
                                break
                        finally:
                            eccodes.codes_release(msg_id)
                break
            except OSError as exc:
                last_error = exc
                time.sleep(0.3 * (attempt + 1))
        else:
            raise GfsWaveParseError(
                f"não foi possível abrir o arquivo temporário após 5 tentativas: {last_error}"
            ) from last_error
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    required = {"swh", "dirpw", "perpw", "ws", "wdir"}
    if not required.intersection(values.keys()):
        raise GfsWaveParseError("dados insuficientes: nenhuma variável esperada encontrada no GRIB2")

    return values


class GfsWaveOceanDataSource(OceanDataSource):
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def _find_working_cycle(self, coordinates: Coordinates) -> datetime:
        """Encontra o ciclo mais recente já publicado, testando o horário
        f000 de cada candidato (mais barato que baixar o dia inteiro só
        para descobrir qual ciclo está disponível)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        last_error: Exception | None = None
        for cycle in candidate_cycles(now):
            url = build_gfswave_grib_filter_url(cycle, coordinates, forecast_hour=0)
            response = await self._http_client.get(url)
            if response.status_code == 404:
                last_error = GfsWaveParseError(f"ciclo {cycle.isoformat()} ainda não publicado (404)")
                continue
            response.raise_for_status()
            return cycle
        raise GfsWaveParseError(
            f"nenhum dos últimos {len(candidate_cycles(now))} ciclos do GFS-Wave está disponível"
        ) from last_error

    async def _fetch_grib_at_hour(
        self, coordinates: Coordinates, cycle: datetime, forecast_hour: int
    ) -> dict[str, float] | None:
        """Busca um horário de previsão específico dentro de um ciclo já
        confirmado como publicado. Devolve None (em vez de levantar erro) se
        esse horário específico ainda não estiver disponível -- permite que
        quem chama monte uma média com os horários que deram certo."""
        url = build_gfswave_grib_filter_url(cycle, coordinates, forecast_hour=forecast_hour)
        response = await self._http_client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            return parse_gfswave_grib2(response.content, coordinates)
        except GfsWaveParseError:
            return None

    async def _fetch_grib(self, coordinates: Coordinates) -> dict[str, float]:
        """Um único ponto no tempo (f000 do ciclo mais recente) -- usado por
        fetch_wave, que reporta a condição atual, não uma média diária."""
        cycle = await self._find_working_cycle(coordinates)
        values = await self._fetch_grib_at_hour(coordinates, cycle, forecast_hour=0)
        if values is None:
            raise GfsWaveParseError(f"ciclo {cycle.isoformat()} não retornou dados válidos em f000")
        return values

    async def fetch_wave(self, coordinates: Coordinates) -> WaveReading:
        values = await self._fetch_grib(coordinates)
        return WaveReading(
            height_m=values["swh"],
            period_s=values["perpw"],
            direction_deg=values["dirpw"],
            observed_at=datetime.now(timezone.utc),
        )

    async def fetch_wind(self, coordinates: Coordinates) -> WindReading:
        """Média das velocidades ao longo do dia (00h-21h, de 3 em 3h),
        para ficar comparável com a metodologia do Open-Meteo (que faz
        média das 24 leituras horárias). Direção reportada é a do primeiro
        horário que deu certo -- média circular de direção é mais complexa
        e o script original também não fazia isso."""
        cycle = await self._find_working_cycle(coordinates)

        speeds: list[float] = []
        direction: float | None = None
        for hour in DAILY_AVERAGE_FORECAST_HOURS:
            values = await self._fetch_grib_at_hour(coordinates, cycle, hour)
            if values is None or "ws" not in values:
                continue
            speeds.append(values["ws"])
            if direction is None and "wdir" in values:
                direction = values["wdir"]

        if not speeds:
            raise GfsWaveParseError(
                f"nenhum horário do dia (ciclo {cycle.isoformat()}) retornou dado de vento válido"
            )

        return WindReading(
            speed_ms=sum(speeds) / len(speeds),
            gust_ms=max(speeds),  # rajada aproximada: maior velocidade do dia
            direction_deg=direction if direction is not None else 0.0,
            observed_at=datetime.now(timezone.utc),
        )