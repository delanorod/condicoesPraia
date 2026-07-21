from datetime import datetime, timezone

import pytest

from app.application.exceptions import BeachNotFoundError, NoStoredConditionError
from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.repositories import CoastalConditionRepository
from app.domain.value_objects import Coordinates
from tests.unit.application.test_use_cases import FakeBeachRepository

COPACABANA = Beach(id="copacabana", name="Copacabana",
                    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897))


def make_condition(beach: Beach) -> CoastalCondition:
    when = datetime(2026, 7, 15, 6, 0, tzinfo=timezone.utc)
    return CoastalCondition(
        beach=beach,
        wind=WindReading(speed_ms=3.5, gust_ms=3.5, direction_deg=63.5, observed_at=when),
        wave=WaveReading(height_m=1.38, period_s=10.5, direction_deg=154.6, observed_at=when),
    )


class FakeCoastalConditionRepository(CoastalConditionRepository):
    def __init__(self, latest_by_beach: dict[str, CoastalCondition] | None = None):
        self._latest_by_beach = latest_by_beach or {}
        self.saved: list[CoastalCondition] = []

    async def save(self, condition: CoastalCondition) -> None:
        self.saved.append(condition)
        self._latest_by_beach[condition.beach.id] = condition

    async def get_latest_by_beach(self, beach_id: str) -> CoastalCondition | None:
        return self._latest_by_beach.get(beach_id)


@pytest.mark.asyncio
class TestGetStoredCoastalConditionUseCase:
    async def test_retorna_a_condicao_mais_recente_salva(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        condition = make_condition(COPACABANA)
        condition_repo = FakeCoastalConditionRepository({"copacabana": condition})
        use_case = GetStoredCoastalConditionUseCase(beach_repo, condition_repo)

        result = await use_case.execute(beach_id="copacabana")

        assert result.wave.height_m == 1.38

    async def test_levanta_erro_para_praia_inexistente(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        condition_repo = FakeCoastalConditionRepository()
        use_case = GetStoredCoastalConditionUseCase(beach_repo, condition_repo)

        with pytest.raises(BeachNotFoundError):
            await use_case.execute(beach_id="inexistente")

    async def test_levanta_erro_quando_praia_existe_mas_nao_tem_condicao_salva(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        condition_repo = FakeCoastalConditionRepository()  # vazio
        use_case = GetStoredCoastalConditionUseCase(beach_repo, condition_repo)

        with pytest.raises(NoStoredConditionError, match="copacabana"):
            await use_case.execute(beach_id="copacabana")
