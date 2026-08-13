"""Adapter para o NOAA GFS-Wave (WAVEWATCH III) via NOMADS.

Dados de domínio público do governo dos EUA (17 U.S.C. § 105), sem qualquer
restrição de uso comercial — ao contrário das fontes anteriores testadas
(Open-Meteo: não comercial; PacIOOS: cortesia acadêmica ambígua).

IMPORTANTE — LIMITE DE VALIDAÇÃO:
Este adapter foi escrito com base na documentação pública do NOMADS/NCEP,
mas o ambiente onde foi desenvolvido não tem acesso de rede a
nomads.ncep.noaa.gov (apenas a repositórios de pacotes). Isso significa que
a URL exata do "GRIB filter" (nomes dos parâmetros de query) NÃO foi testada
contra o servidor real. A seleção de ciclo e o parsing de bytes GRIB2 (via
eccodes) seguem a documentação oficial, mas só serão confirmados quando você
rodar isso na sua máquina, com internet completa. Use o script
`scripts/verificar_nomads.py` (fornecido à parte) para checar rapidamente,
fora do resto da aplicação, se a URL está correta antes de confiar na API
inteira.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.domain.entities import WaveReading, WindReading
from app.domain.repositories import OceanDataSource
from app.domain.value_objects import Coordinates

NOMADS_GFSWAVE_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfswave.pl"
CYCLE_HOURS = (0, 6, 12, 18)
PUBLISH_DELAY_HOURS = 5  # margem de segurança; NOAA costuma publicar ~4h-4h30 depois do ciclo
GRID_STEP_DEG = 0.25  # resolução do GFS-Wave 0p25
SEARCH_BOX_DEG = 1.5  # ampliado após localidades em baías bem fechadas
# (Angra dos Reis) não acharem nenhum ponto de mar válido com 0.75


def select_latest_available_cycle(now_utc: datetime, publish_delay_hours: int = PUBLISH_DELAY_HOURS) -> datetime:
    """Ciclo de previsão (00/06/12/18 UTC) mais recente que já deve estar publicado."""
    cycle_hour = (now_utc.hour // 6) * 6
    cycle = now_utc.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)
    while now_utc < cycle + timedelta(hours=publish_delay_hours):
        cycle -= timedelta(hours=6)
    return cycle


def candidate_cycles(now_utc: datetime, max_attempts: int = 4) -> list[datetime]:
    """Lista de ciclos a tentar, do mais recente ao mais antigo.

    Na prática o atraso de publicação da NOAA varia (não é sempre exatos
    5h), então em vez de confiar cegamente em `select_latest_available_cycle`
    e falhar se aquele ciclo específico ainda não estiver pronto, tentamos
    ele e alguns anteriores em sequência.
    """
    first = select_latest_available_cycle(now_utc)
    return [first - timedelta(hours=6 * i) for i in range(max_attempts)]


def build_gfswave_grib_filter_url(cycle: datetime, coordinates: Coordinates, forecast_hour: int = 0) -> str:
    """Monta a URL do GRIB filter do NOMADS para uma caixa mínima ao redor do ponto.

    NÃO VALIDADO CONTRA O SERVIDOR REAL — ver aviso no topo do arquivo.
    Convenção de parâmetros baseada na documentação pública do NOMADS filter
    CGI (mesmo padrão usado em filter_gfs_0p25.pl): var_<NOME>=on por
    variável, subregion com left/right/top/bottom lon/lat, e dir apontando
    para o diretório do ciclo no servidor.
    """
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
    """Resposta do NOMADS vazia, não é GRIB2 válido, ou variável esperada ausente."""


def parse_gfswave_grib2(raw_bytes: bytes, coordinates: Coordinates) -> dict[str, float]:
    """Extrai HTSGW, DIRPW, PERPW, WIND, WDIR do ponto de grade mais próximo.

    Usa a biblioteca `eccodes` (pip install eccodes — desde a versão 2.37 traz
    o binário embutido também no Windows, sem precisar compilar nada).
    NÃO VALIDADO contra um arquivo GRIB2 real neste ambiente — ver aviso no
    topo do arquivo.
    """
    if not raw_bytes.startswith(b"GRIB"):
        raise GfsWaveParseError("resposta do NOMADS não é um arquivo GRIB2 válido")

    import os
    import tempfile

    import eccodes

    values: dict[str, float] = {}
    # eccodes.codes_grib_new_from_file precisa de um arquivo real em disco
    # (usa fileno() internamente) — não aceita BytesIO. No Windows, um
    # antivírus/indexador pode travar o arquivo por uma fração de segundo
    # logo após ser criado ("WinError 32"); por isso tentamos algumas vezes
    # com uma pequena espera entre as tentativas.
    import time

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

                            # WAVEWATCH III só calcula sobre o mar: o ponto de
                            # grade mais próximo pode cair em terra (valor
                            # sentinela, tipicamente 9999). Pedimos os 4
                            # vizinhos mais próximos e usamos o primeiro que
                            # não for terra/ausente.
                            candidates = eccodes.codes_grib_find_nearest(
                                msg_id, coordinates.latitude, coordinates.longitude, npoints=4
                            )
                            for candidate in candidates:
                                value = candidate.value
                                if missing_value is not None and value == missing_value:
                                    continue
                                if value in (9999.0, 9999):  # sentinela de segurança
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
            pass  # limpeza best-effort; não deve mascarar um erro real acima

    required = {"swh", "dirpw", "perpw", "ws", "wdir"}  # confirmado contra resposta real do NOMADS
    if not required.intersection(values.keys()):
        raise GfsWaveParseError("dados insuficientes: nenhuma variável esperada encontrada no GRIB2")

    return values


class GfsWaveOceanDataSource(OceanDataSource):
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def _fetch_grib(self, coordinates: Coordinates) -> dict[str, float]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        last_error: Exception | None = None
        for cycle in candidate_cycles(now):
            url = build_gfswave_grib_filter_url(cycle, coordinates)
            response = await self._http_client.get(url)
            if response.status_code == 404:
                last_error = GfsWaveParseError(f"ciclo {cycle.isoformat()} ainda não publicado (404)")
                continue
            response.raise_for_status()
            return parse_gfswave_grib2(response.content, coordinates)
        raise GfsWaveParseError(
            f"nenhum dos últimos {len(candidate_cycles(now))} ciclos do GFS-Wave está disponível"
        ) from last_error

    async def fetch_wave(self, coordinates: Coordinates) -> WaveReading:
        values = await self._fetch_grib(coordinates)
        return WaveReading(
            height_m=values["swh"],
            period_s=values["perpw"],
            direction_deg=values["dirpw"],
            observed_at=datetime.now(timezone.utc),
        )

    async def fetch_wind(self, coordinates: Coordinates) -> WindReading:
        values = await self._fetch_grib(coordinates)
        speed = values["ws"]
        return WindReading(
            speed_ms=speed,
            gust_ms=speed,  # GFS-Wave não inclui rajada; usar a mesma velocidade como aproximação
            direction_deg=values["wdir"],
            observed_at=datetime.now(timezone.utc),
        )
