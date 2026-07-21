"""Portas do domínio (interfaces). A infraestrutura implementa; a aplicação depende só disto."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.value_objects import Coordinates


class BeachRepository(ABC):
    @abstractmethod
    async def get_all(self) -> list[Beach]: ...

    @abstractmethod
    async def get_by_id(self, beach_id: str) -> Beach | None: ...


class OceanDataSource(ABC):
    """Porta para qualquer fonte de dados de vento/onda (Open-Meteo, ou outra no futuro)."""

    @abstractmethod
    async def fetch_wind(self, coordinates: Coordinates) -> WindReading: ...

    @abstractmethod
    async def fetch_wave(self, coordinates: Coordinates) -> WaveReading: ...


class CoastalConditionRepository(ABC):
    """Persistência histórica das condições observadas (PostGIS)."""

    @abstractmethod
    async def save(self, condition: CoastalCondition) -> None: ...

    @abstractmethod
    async def get_latest_by_beach(self, beach_id: str) -> CoastalCondition | None: ...
