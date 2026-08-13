from app.domain.scoring import calculate_beach_score


class TestCalculateBeachScore:
    def test_balneabilidade_propria_soma_100(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                      agitation=None, balneability="propria") == 100

    def test_balneabilidade_impropria_subtrai_100(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                      agitation=None, balneability="impropria") == -100

    def test_balneabilidade_none_nao_soma_nem_subtrai(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                      agitation=None, balneability=None) == 0

    def test_onda_abaixo_de_0_5_soma_40(self):
        assert calculate_beach_score(wave_height_m=0.3, wind_speed_kmh=None,
                                      agitation=None, balneability=None) == 40

    def test_onda_entre_0_5_e_1_0_soma_30(self):
        assert calculate_beach_score(wave_height_m=0.7, wind_speed_kmh=None,
                                      agitation=None, balneability=None) == 30

    def test_onda_entre_1_0_e_1_5_soma_10(self):
        assert calculate_beach_score(wave_height_m=1.2, wind_speed_kmh=None,
                                      agitation=None, balneability=None) == 10

    def test_onda_1_5_ou_mais_subtrai_10(self):
        assert calculate_beach_score(wave_height_m=1.5, wind_speed_kmh=None,
                                      agitation=None, balneability=None) == -10

    def test_vento_abaixo_de_10_kmh_soma_30(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=5.0,
                                      agitation=None, balneability=None) == 30

    def test_vento_entre_10_e_20_kmh_soma_15(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=15.0,
                                      agitation=None, balneability=None) == 15

    def test_vento_entre_20_e_30_kmh_nao_soma_nem_subtrai(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=25.0,
                                      agitation=None, balneability=None) == 0

    def test_vento_acima_de_30_kmh_subtrai_20(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=35.0,
                                      agitation=None, balneability=None) == -20

    def test_agitacao_forte_subtrai_20(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                      agitation="Forte", balneability=None) == -20

    def test_agitacao_moderado_subtrai_5(self):
        assert calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                      agitation="Moderado", balneability=None) == -5

    def test_combina_todos_os_fatores(self):
        # praia própria, onda calma, vento fraco, sem agitação forte -> score alto
        score = calculate_beach_score(wave_height_m=0.3, wind_speed_kmh=5.0,
                                       agitation=None, balneability="propria")
        assert score == 100 + 40 + 30  # 170

    def test_caracteristica_familiar_soma_25(self):
        score = calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                       agitation=None, balneability=None,
                                       characteristics=["familiar", "tranquila"])
        assert score == 25

    def test_caracteristica_surf_subtrai_15(self):
        score = calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                       agitation=None, balneability=None,
                                       characteristics=["surf"])
        assert score == -15

    def test_caracteristica_selvagem_subtrai_15(self):
        score = calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                       agitation=None, balneability=None,
                                       characteristics=["APA", "selvagem"])
        assert score == -15

    def test_sem_caracteristicas_nao_afeta_score(self):
        score = calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                       agitation=None, balneability=None,
                                       characteristics=None)
        assert score == 0

    def test_lista_vazia_de_caracteristicas_nao_afeta_score(self):
        score = calculate_beach_score(wave_height_m=None, wind_speed_kmh=None,
                                       agitation=None, balneability=None,
                                       characteristics=[])
        assert score == 0
