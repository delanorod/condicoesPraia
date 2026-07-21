"""Casos de uso: orquestram entidades e portas do domínio, sem lógica de negócio própria."""
from __future__ import annotations

import asyncio

from app.application.exceptions import BeachNotFoundError, NoStoredConditionError
from app.domain.entities import CoastalCondition
from app.domain.repositories import BeachRepository, CoastalConditionRepository, OceanDataSource


class GetCoastalConditionUseCase:
    def __init__(self, beach_repository: BeachRepository, ocean_data_source: OceanDataSource):
        self._beach_repository = beach_repository
        self._ocean_data_source = ocean_data_source

    async def execute(self, beach_id: str) -> CoastalCondition:
        beach = await self._beach_repository.get_by_id(beach_id)
        if beach is None:
            raise BeachNotFoundError(beach_id)

        # Vento e onda são consultas independentes: buscar em paralelo reduz a
        # latência total pela metade em relação a chamadas sequenciais.
        wind, wave = await asyncio.gather(
            self._ocean_data_source.fetch_wind(beach.coordinates),
            self._ocean_data_source.fetch_wave(beach.coordinates),
        )

        return CoastalCondition(beach=beach, wind=wind, wave=wave)


class GetStoredCoastalConditionUseCase:
    """Lê a última condição já salva no banco — rápido, sem chamar a NOAA.

    É esse que a API deve usar para servir o app mobile: buscar ao vivo na
    NOAA a cada abertura do app seria lento e sujeito a instabilidade do
    NOMADS. Um job separado (`scripts/collect_daily_conditions.py`) usa
    `GetCoastalConditionUseCase` para buscar ao vivo e salvar periodicamente.
    """

    def __init__(self, beach_repository: BeachRepository, condition_repository: CoastalConditionRepository):
        self._beach_repository = beach_repository
        self._condition_repository = condition_repository

    async def execute(self, beach_id: str) -> CoastalCondition:
        beach = await self._beach_repository.get_by_id(beach_id)
        if beach is None:
            raise BeachNotFoundError(beach_id)

        condition = await self._condition_repository.get_latest_by_beach(beach_id)
        if condition is None:
            raise NoStoredConditionError(beach_id)

        return condition


class RefreshBalneabilityUseCase:
    """Busca a balneabilidade ao vivo (Praia Limpa/INEA) para todas as praias
    cadastradas e salva. Usado pelo job de coleta, separado do fluxo de
    vento/onda por completo (fonte, frequência e natureza do dado diferentes).
    """

    def __init__(self, beach_repository: BeachRepository, data_source, repository):
        self._beach_repository = beach_repository
        self._data_source = data_source
        self._repository = repository

    async def execute(self) -> dict[str, object]:
        beaches = await self._beach_repository.get_all()
        statuses = await self._data_source.fetch_all(beaches)
        await self._repository.save_all(statuses)
        return statuses
