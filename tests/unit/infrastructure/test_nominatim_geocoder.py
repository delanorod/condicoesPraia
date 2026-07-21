import httpx
import pytest
import respx

from app.infrastructure.nominatim_geocoder import NOMINATIM_URL, NominatimGeocoder

FAKE_RESPONSE = [
    {"lat": "-22.9868", "lon": "-43.1897", "display_name": "Copacabana, Rio de Janeiro, RJ, Brasil"}
]


@pytest.mark.asyncio
class TestNominatimGeocoder:
    async def test_geocodifica_uma_localidade_com_sucesso(self):
        with respx.mock:
            respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(200, json=FAKE_RESPONSE))
            async with httpx.AsyncClient() as client:
                geocoder = NominatimGeocoder(http_client=client, rate_limit_seconds=0)
                coords = await geocoder.geocode("Praia de Copacabana, Rio de Janeiro, RJ, Brasil")

        assert coords is not None
        assert coords.latitude == -22.9868
        assert coords.longitude == -43.1897

    async def test_retorna_none_quando_nao_encontra(self):
        with respx.mock:
            respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(200, json=[]))
            async with httpx.AsyncClient() as client:
                geocoder = NominatimGeocoder(http_client=client, rate_limit_seconds=0)
                coords = await geocoder.geocode("Localidade que não existe, RJ, Brasil")

        assert coords is None

    async def test_envia_user_agent_identificavel(self):
        # Nominatim exige um User-Agent identificável nos termos de uso;
        # requisições anônimas/genéricas podem ser bloqueadas.
        with respx.mock:
            route = respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(200, json=FAKE_RESPONSE))
            async with httpx.AsyncClient() as client:
                geocoder = NominatimGeocoder(http_client=client, rate_limit_seconds=0)
                await geocoder.geocode("Copacabana, RJ, Brasil")

        sent_request = route.calls[0].request
        assert "User-Agent" in sent_request.headers
        assert sent_request.headers["User-Agent"] != ""
