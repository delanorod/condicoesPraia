import pytest

from app.domain.value_objects import Coordinates


class TestCoordinates:
    def test_cria_coordenadas_validas(self):
        coords = Coordinates(latitude=-22.9868, longitude=-43.1729)  # Copacabana
        assert coords.latitude == -22.9868
        assert coords.longitude == -43.1729

    def test_coordenadas_sao_imutaveis(self):
        coords = Coordinates(latitude=-22.9868, longitude=-43.1729)
        with pytest.raises(AttributeError):
            coords.latitude = 0.0

    @pytest.mark.parametrize("latitude", [-90.0, 90.0, 0.0])
    def test_aceita_latitude_nos_limites(self, latitude):
        coords = Coordinates(latitude=latitude, longitude=0.0)
        assert coords.latitude == latitude

    @pytest.mark.parametrize("latitude", [-90.1, 90.1, 200.0])
    def test_rejeita_latitude_fora_dos_limites(self, latitude):
        with pytest.raises(ValueError, match="Latitude"):
            Coordinates(latitude=latitude, longitude=0.0)

    @pytest.mark.parametrize("longitude", [-180.1, 180.1])
    def test_rejeita_longitude_fora_dos_limites(self, longitude):
        with pytest.raises(ValueError, match="Longitude"):
            Coordinates(latitude=0.0, longitude=longitude)

    def test_duas_coordenadas_iguais_sao_iguais(self):
        a = Coordinates(latitude=-22.9868, longitude=-43.1729)
        b = Coordinates(latitude=-22.9868, longitude=-43.1729)
        assert a == b

    def test_distancia_haversine_entre_duas_praias_proximas(self):
        copacabana = Coordinates(latitude=-22.9868, longitude=-43.1897)
        ipanema = Coordinates(latitude=-22.9868, longitude=-43.2044)
        distancia_km = copacabana.distance_to(ipanema)
        # Copacabana-Ipanema ~1.5km em linha reta
        assert 1.0 < distancia_km < 2.5
