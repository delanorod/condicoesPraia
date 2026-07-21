import pytest

from app.application.use_cases import RefreshBalneabilityUseCase
from app.domain.entities import Beach
from app.domain.value_objects import Coordinates
from app.infrastructure.praia_limpa_client import BalneabilityStatus
from tests.unit.application.test_use_cases import FakeBeachRepository

COPACABANA = Beach(id="copacabana", name="Copacabana",
                    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897))
IPANEMA = Beach(id="ipanema", name="Ipanema",
                 coordinates=Coordinates(latitude=-22.9868, longitude=-43.2044))


class FakeBalneabilityDataSource:
    def __init__(self, statuses: dict[str, BalneabilityStatus]):
        self._statuses = statuses
        self.received_beaches: list[Beach] | None = None

    async def fetch_all(self, known_beaches):
        self.received_beaches = known_beaches
        return self._statuses


class FakeBalneabilityRepository:
    def __init__(self):
        self.saved: dict[str, BalneabilityStatus] = {}

    async def save_all(self, statuses: dict[str, BalneabilityStatus]) -> None:
        self.saved.update(statuses)

    async def get_latest_by_beach(self, beach_id: str) -> BalneabilityStatus | None:
        return self.saved.get(beach_id)


@pytest.mark.asyncio
class TestRefreshBalneabilityUseCase:
    async def test_busca_status_para_todas_as_praias_cadastradas_e_salva(self):
        beach_repo = FakeBeachRepository([COPACABANA, IPANEMA])
        data_source = FakeBalneabilityDataSource({"copacabana": BalneabilityStatus.PROPRIA})
        repo = FakeBalneabilityRepository()
        use_case = RefreshBalneabilityUseCase(beach_repo, data_source, repo)

        result = await use_case.execute()

        assert data_source.received_beaches == [COPACABANA, IPANEMA]
        assert repo.saved == {"copacabana": BalneabilityStatus.PROPRIA}
        assert result == {"copacabana": BalneabilityStatus.PROPRIA}
