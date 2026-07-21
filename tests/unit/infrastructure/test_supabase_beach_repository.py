from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities import Beach
from app.domain.value_objects import Coordinates
from app.infrastructure.supabase_repository import SupabaseBeachRepository


def make_client_with_rows(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    execute_result = MagicMock(data=rows)
    # client.table("beaches").select("*").execute() -> encadeamento fluente
    query = MagicMock()
    query.execute = AsyncMock(return_value=execute_result)
    query.select.return_value = query
    query.eq.return_value = query
    client.table.return_value = query
    return client


class TestSupabaseBeachRepository:
    @pytest.mark.asyncio
    async def test_get_all_converte_linhas_em_entidades_beach(self):
        rows = [
            {"id": "copacabana", "name": "Copacabana", "latitude": -22.9868, "longitude": -43.1897},
            {"id": "ipanema", "name": "Ipanema", "latitude": -22.9868, "longitude": -43.2044},
        ]
        client = make_client_with_rows(rows)
        repo = SupabaseBeachRepository(client)

        beaches = await repo.get_all()

        assert beaches == [
            Beach(id="copacabana", name="Copacabana",
                  coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897)),
            Beach(id="ipanema", name="Ipanema",
                  coordinates=Coordinates(latitude=-22.9868, longitude=-43.2044)),
        ]

    @pytest.mark.asyncio
    async def test_get_by_id_retorna_none_quando_nao_encontrada(self):
        client = make_client_with_rows([])
        repo = SupabaseBeachRepository(client)

        assert await repo.get_by_id("inexistente") is None

    @pytest.mark.asyncio
    async def test_get_by_id_retorna_a_praia_encontrada(self):
        rows = [{"id": "copacabana", "name": "Copacabana", "latitude": -22.9868, "longitude": -43.1897}]
        client = make_client_with_rows(rows)
        repo = SupabaseBeachRepository(client)

        beach = await repo.get_by_id("copacabana")

        assert beach.id == "copacabana"
        assert beach.coordinates.latitude == -22.9868
