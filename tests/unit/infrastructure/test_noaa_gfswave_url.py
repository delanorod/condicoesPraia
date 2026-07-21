from datetime import datetime

from app.domain.value_objects import Coordinates
from app.infrastructure.noaa_gfswave_client import build_gfswave_grib_filter_url

COPACABANA = Coordinates(latitude=-22.9868, longitude=-43.1897)


class TestBuildGfswaveGribFilterUrl:
    def test_url_contem_nome_do_arquivo_com_ciclo_correto(self):
        cycle = datetime(2026, 7, 13, 6, 0)
        url = build_gfswave_grib_filter_url(cycle, COPACABANA)
        assert "gfswave.t06z.global.0p25.f000.grib2" in url

    def test_url_referencia_diretorio_do_ciclo(self):
        cycle = datetime(2026, 7, 13, 6, 0)
        url = build_gfswave_grib_filter_url(cycle, COPACABANA)
        assert "dir=%2Fgfs.20260713%2F06%2Fwave%2Fgridded" in url or "dir=/gfs.20260713/06/wave/gridded" in url

    def test_caixa_geografica_envolve_o_ponto_pedido(self):
        cycle = datetime(2026, 7, 13, 6, 0)
        url = build_gfswave_grib_filter_url(cycle, COPACABANA)
        # longitude convertida para 0-360 (convenção do GFS): -43.1897 -> 316.81...
        assert "toplat=-21.4868" in url
        assert "bottomlat=-24.4868" in url

    def test_inclui_todas_as_variaveis_necessarias(self):
        cycle = datetime(2026, 7, 13, 6, 0)
        url = build_gfswave_grib_filter_url(cycle, COPACABANA)
        for var in ("var_HTSGW", "var_DIRPW", "var_PERPW", "var_WIND", "var_WDIR"):
            assert f"{var}=on" in url
