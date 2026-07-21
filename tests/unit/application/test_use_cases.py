from datetime import datetime, timezone

import pytest

from app.application.exceptions import BeachNotFoundError
from app.application.use_cases import GetCoastalConditionUseCase
from app.domain.entities import Beach, WaveReading, WindReading
from app.domain.repositories import BeachRepository, OceanDataSource
from app.domain.value_objects import Coordinates

COPACABANA = Beach(
    id="copacabana",
    name="Copacabana",
    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897),
)


class FakeBeachRepository(BeachRepository):
    def __init__(self, beaches: list[Beach]):
        self._beaches = {b.id: b for b in beaches}

    async def get_all(self) -> list[Beach]:
        return list(self._beaches.values())

    async def get_by_id(self, beach_id: str) -> Beach | None:
        return self._beaches.get(beach_id)


class FakeOceanDataSource(OceanDataSource):
    def __init__(self, wind: WindReading, wave: WaveReading):
        self._wind = wind
        self._wave = wave
        self.requested_coordinates: list[Coordinates] = []

    async def fetch_wind(self, coordinates: Coordinates) -> WindReading:
        self.requested_coordinates.append(coordinates)
        return self._wind

    async def fetch_wave(self, coordinates: Coordinates) -> WaveReading:
        self.requested_coordinates.append(coordinates)
        return self._wave


def make_wind() -> WindReading:
    return WindReading(speed_ms=6.2, gust_ms=8.1, direction_deg=90.0,
                        observed_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc))


def make_wave(height_m: float = 1.8) -> WaveReading:
    return WaveReading(height_m=height_m, period_s=8.0, direction_deg=135.0,
                        observed_at=datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc))


@pytest.mark.asyncio
class TestGetCoastalConditionUseCase:
    async def test_retorna_condicao_costeira_para_praia_existente(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        ocean_source = FakeOceanDataSource(wind=make_wind(), wave=make_wave())
        use_case = GetCoastalConditionUseCase(beach_repo, ocean_source)

        condition = await use_case.execute(beach_id="copacabana")

        assert condition.beach.id == "copacabana"
        assert condition.wind.speed_ms == 6.2
        assert condition.wave.height_m == 1.8

    async def test_consulta_a_estacao_noaa_correta_da_praia(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        ocean_source = FakeOceanDataSource(wind=make_wind(), wave=make_wave())
        use_case = GetCoastalConditionUseCase(beach_repo, ocean_source)

        await use_case.execute(beach_id="copacabana")

        assert ocean_source.requested_coordinates == [COPACABANA.coordinates, COPACABANA.coordinates]

    async def test_levanta_erro_para_praia_inexistente(self):
        beach_repo = FakeBeachRepository([COPACABANA])
        ocean_source = FakeOceanDataSource(wind=make_wind(), wave=make_wave())
        use_case = GetCoastalConditionUseCase(beach_repo, ocean_source)

        with pytest.raises(BeachNotFoundError, match="praia-inexistente"):
            await use_case.execute(beach_id="praia-inexistente")
