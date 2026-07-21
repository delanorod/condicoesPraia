from app.infrastructure.import_praias_rj import convert_praias_rj_json


class TestConvertPraiasRjJson:
    def test_converte_praia_basica(self):
        data = {
            "praias": [
                {
                    "nome": "Leme", "lat": -22.9635, "lon": -43.1674,
                    "municipio": "Rio de Janeiro", "bairro": "Leme", "regiao": "Zona Sul",
                }
            ]
        }
        beaches = convert_praias_rj_json(data)

        assert len(beaches) == 1
        beach = beaches[0]
        assert beach.name == "Leme"
        assert beach.coordinates.latitude == -22.9635
        assert beach.coordinates.longitude == -43.1674
        assert beach.municipality == "Rio de Janeiro"
        assert beach.neighborhood == "Leme"
        assert beach.region == "Zona Sul"

    def test_gera_id_com_nome_e_municipio_para_evitar_colisao(self):
        data = {
            "praias": [
                {"nome": "Vermelha", "lat": -22.95, "lon": -43.16,
                 "municipio": "Rio de Janeiro", "bairro": "Urca", "regiao": "Zona Sul"},
            ]
        }
        beaches = convert_praias_rj_json(data)
        assert beaches[0].id == "vermelha-rio-de-janeiro"

    def test_pula_praias_sem_coordenadas(self):
        data = {
            "praias": [
                {"nome": "Sem Coordenada", "lat": None, "lon": None,
                 "municipio": "Rio de Janeiro", "bairro": "X", "regiao": "Y"},
                {"nome": "Com Coordenada", "lat": -22.9, "lon": -43.1,
                 "municipio": "Rio de Janeiro", "bairro": "X", "regiao": "Y"},
            ]
        }
        beaches = convert_praias_rj_json(data)
        assert len(beaches) == 1
        assert beaches[0].name == "Com Coordenada"
