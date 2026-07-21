from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.value_objects import Coordinates
from app.infrastructure.supabase_repository import SupabaseCoastalConditionRepository

COPACABANA = Beach(id="copacabana", name="Copacabana",
                    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897))


def make_condition() -> CoastalCondition:
    when = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    return CoastalCondition(
        beach=COPACABANA,
        wind=WindReading(speed_ms=3.5, gust_ms=3.5, direction_deg=63.5, observed_at=when),
        wave=WaveReading(height_m=1.38, period_s=10.5, direction_deg=154.6, observed_at=when),
    )


class FakeBeachRepo:
    async def get_by_id(self, beach_id):
        return COPACABANA if beach_id == "copacabana" else None

    async def get_all(self):
        return [COPACABANA]


def make_client_for_insert() -> MagicMock:
    client = MagicMock()
    query = MagicMock()
    query.execute = AsyncMock(return_value=MagicMock(data=[{}]))
    query.insert.return_value = query
    client.table.return_value = query
    return client


def make_client_for_select(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    query = MagicMock()
    query.execute = AsyncMock(return_value=MagicMock(data=rows))
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    client.table.return_value = query
    return client


class TestSupabaseCoastalConditionRepositorySave:
    @pytest.mark.asyncio
    async def test_envia_insert_com_todos_os_campos(self):
        client = make_client_for_insert()
        repo = SupabaseCoastalConditionRepository(client, beach_repository=FakeBeachRepo())

        await repo.save(make_condition())

        query = client.table.return_value
        query.insert.assert_called_once()
        payload = query.insert.call_args[0][0]
        assert payload["beach_id"] == "copacabana"
        assert payload["wave_height_m"] == 1.38
        assert payload["sea_state"] == "moderado"


class TestSupabaseCoastalConditionRepositoryGetLatest:
    @pytest.mark.asyncio
    async def test_retorna_none_quando_nao_ha_condicao_salva(self):
        client = make_client_for_select([])
        repo = SupabaseCoastalConditionRepository(client, beach_repository=FakeBeachRepo())

        assert await repo.get_latest_by_beach("copacabana") is None

    @pytest.mark.asyncio
    async def test_reconstroi_coastal_condition_a_partir_da_linha(self):
        rows = [{
            "beach_id": "copacabana",
            "observed_at": "2026-07-15T06:00:00+00:00",
            "wind_speed_ms": 3.5, "wind_gust_ms": 3.5, "wind_direction_deg": 63.5,
            "wave_height_m": 1.38, "wave_period_s": 10.5, "wave_direction_deg": 154.6,
            "sea_state": "moderado",
        }]
        client = make_client_for_select(rows)
        repo = SupabaseCoastalConditionRepository(client, beach_repository=FakeBeachRepo())

        condition = await repo.get_latest_by_beach("copacabana")

        assert condition.wave.height_m == 1.38
        assert condition.beach.id == "copacabana"
