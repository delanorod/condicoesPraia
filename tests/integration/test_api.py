from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.value_objects import Coordinates
from app.infrastructure.api.dependencies import get_beach_repository, get_stored_coastal_condition_use_case
from app.infrastructure.api.main import app
from tests.unit.application.test_use_cases import FakeBeachRepository
from tests.unit.application.test_get_stored_condition import FakeCoastalConditionRepository

COPACABANA = Beach(
    id="copacabana",
    name="Copacabana",
    coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897),
)
IPANEMA = Beach(
    id="ipanema",
    name="Ipanema",
    coordinates=Coordinates(latitude=-22.9868, longitude=-43.2044),
)


def _condition(beach: Beach, height_m: float = 1.8) -> CoastalCondition:
    when = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    return CoastalCondition(
        beach=beach,
        wind=WindReading(speed_ms=6.2, gust_ms=8.1, direction_deg=90.0, observed_at=when),
        wave=WaveReading(height_m=height_m, period_s=8.0, direction_deg=135.0, observed_at=when),
    )


@pytest.fixture
def client():
    beach_repo = FakeBeachRepository([COPACABANA, IPANEMA])
    condition_repo = FakeCoastalConditionRepository({"copacabana": _condition(COPACABANA)})
    use_case = GetStoredCoastalConditionUseCase(beach_repository=beach_repo, condition_repository=condition_repo)

    app.dependency_overrides[get_stored_coastal_condition_use_case] = lambda: use_case
    app.dependency_overrides[get_beach_repository] = lambda: beach_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetCoastalConditionEndpoint:
    def test_retorna_200_com_condicao_da_praia(self, client):
        response = client.get("/praias/copacabana/condicoes")

        assert response.status_code == 200
        body = response.json()
        assert body["praia"]["nome"] == "Copacabana"
        assert body["vento"]["velocidade_ms"] == 6.2
        assert body["onda"]["altura_m"] == 1.8
        assert body["estado_do_mar"] == "moderado"

    def test_retorna_404_para_praia_inexistente(self, client):
        response = client.get("/praias/inexistente/condicoes")

        assert response.status_code == 404
        assert "inexistente" in response.json()["detail"]

    def test_retorna_503_quando_praia_existe_mas_sem_condicao_salva(self, client):
        response = client.get("/praias/ipanema/condicoes")
        assert response.status_code == 503

    def test_healthcheck(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestListBeachesEndpoint:
    def test_retorna_lista_de_praias_cadastradas(self, client):
        response = client.get("/praias")

        assert response.status_code == 200
        ids = {praia["id"] for praia in response.json()}
        assert "copacabana" in ids
