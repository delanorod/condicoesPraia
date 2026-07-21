"""Geocodificação via Nominatim (OpenStreetMap) -- gratuito, sem chave de
API. Usado apenas pelo script de geração de seed (rodado uma vez, não em
tempo de requisição da API), então o rate limit da política de uso pública
do Nominatim (máx. 1 requisição/segundo) não afeta a aplicação em produção.

Política de uso: https://operations.osmfoundation.org/policies/nominatim/
Exige um User-Agent identificável -- requisições anônimas podem ser
bloqueadas.
"""
from __future__ import annotations

import asyncio

import httpx

from app.domain.value_objects import Coordinates

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "beach-conditions-api/1.0 (uso pessoal -- geocodificacao de praias do RJ)"


class NominatimGeocoder:
    def __init__(self, http_client: httpx.AsyncClient, rate_limit_seconds: float = 1.1):
        self._http_client = http_client
        self._rate_limit_seconds = rate_limit_seconds

    async def geocode(self, query: str) -> Coordinates | None:
        response = await self._http_client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()

        if self._rate_limit_seconds > 0:
            await asyncio.sleep(self._rate_limit_seconds)

        results = response.json()
        if not results:
            return None

        return Coordinates(latitude=float(results[0]["lat"]), longitude=float(results[0]["lon"]))
