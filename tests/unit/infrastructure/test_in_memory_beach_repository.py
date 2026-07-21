import pytest

from app.domain.entities import Beach
from app.domain.value_objects import Coordinates
from app.infrastructure.in_memory_beach_repository import InMemoryBeachRepository

COPACABANA = Beach(id="copacabana", name="Copacabana",
                    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897))
IPANEMA = Beach(id="ipanema", name="Ipanema",
                 coordinates=Coordinates(latitude=-22.9868, longitude=-43.2044))


@pytest.mark.asyncio
class TestInMemoryBeachRepository:
    async def test_get_all_retorna_todas_as_praias_cadastradas(self):
        repo = InMemoryBeachRepository([COPACABANA, IPANEMA])
        beaches = await repo.get_all()
        assert {b.id for b in beaches} == {"copacabana", "ipanema"}

    async def test_get_by_id_retorna_praia_existente(self):
        repo = InMemoryBeachRepository([COPACABANA])
        beach = await repo.get_by_id("copacabana")
        assert beach == COPACABANA

    async def test_get_by_id_retorna_none_para_praia_inexistente(self):
        repo = InMemoryBeachRepository([COPACABANA])
        assert await repo.get_by_id("inexistente") is None
