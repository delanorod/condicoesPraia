"""Composition root da API: aqui, e só aqui, a infraestrutura concreta é
escolhida e ligada aos casos de uso. Domínio e aplicação não sabem disso."""
from __future__ import annotations

from functools import lru_cache

import httpx
from fastapi import Depends
from supabase import AsyncClient, acreate_client

from app.application.use_cases import GetCoastalConditionUseCase, GetStoredCoastalConditionUseCase
from app.config import settings
from app.infrastructure.noaa_gfswave_client import GfsWaveOceanDataSource
from app.infrastructure.supabase_repository import (
    SupabaseBalneabilityRepository,
    SupabaseBeachRepository,
    SupabaseCoastalConditionRepository,
)

_supabase_client: AsyncClient | None = None


async def get_supabase_client() -> AsyncClient:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await acreate_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


async def get_beach_repository(
    client: AsyncClient = Depends(get_supabase_client),
) -> SupabaseBeachRepository:
    return SupabaseBeachRepository(client)


async def get_condition_repository(
    client: AsyncClient = Depends(get_supabase_client),
    beach_repository: SupabaseBeachRepository = Depends(get_beach_repository),
) -> SupabaseCoastalConditionRepository:
    return SupabaseCoastalConditionRepository(client, beach_repository=beach_repository)


async def get_balneability_repository(
    client: AsyncClient = Depends(get_supabase_client),
) -> SupabaseBalneabilityRepository:
    return SupabaseBalneabilityRepository(client)


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30.0)


def get_ocean_data_source() -> GfsWaveOceanDataSource:
    return GfsWaveOceanDataSource(http_client=get_http_client())


async def get_coastal_condition_use_case(
    beach_repository: SupabaseBeachRepository = Depends(get_beach_repository),
) -> GetCoastalConditionUseCase:
    """Busca AO VIVO na NOAA. Usado pelo job de coleta, não pela API mobile."""
    return GetCoastalConditionUseCase(
        beach_repository=beach_repository,
        ocean_data_source=get_ocean_data_source(),
    )


async def get_stored_coastal_condition_use_case(
    beach_repository: SupabaseBeachRepository = Depends(get_beach_repository),
    condition_repository: SupabaseCoastalConditionRepository = Depends(get_condition_repository),
) -> GetStoredCoastalConditionUseCase:
    """Lê do banco — rápido, é o que a API mobile usa."""
    return GetStoredCoastalConditionUseCase(
        beach_repository=beach_repository,
        condition_repository=condition_repository,
    )
