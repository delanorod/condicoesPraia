from unittest.mock import MagicMock, patch

import pytest

from app.domain.value_objects import Coordinates
from app.infrastructure.noaa_gfswave_client import GfsWaveParseError, parse_gfswave_grib2

COPACABANA = Coordinates(latitude=-22.9868, longitude=-43.1897)

# Bytes mágicos reais de um GRIB2 (o conteúdo interno é irrelevante aqui:
# eccodes é mockado, só o prefixo é checado antes de chamar a biblioteca).
FAKE_GRIB2_BYTES = b"GRIB" + b"\x00" * 20

MISSING_VALUE = 9999.0


def _codes_get_side_effect(short_names: dict[int, str]):
    """codes_get(msg_id, key) -> shortName do msg_id, ou o sentinela de
    'ausente' quando perguntado por missingValue."""
    def fn(msg_id, key):
        if key == "shortName":
            return short_names[msg_id]
        if key == "missingValue":
            return MISSING_VALUE
        raise AssertionError(f"chave inesperada: {key}")
    return fn


class TestParseGfswaveGrib2:
    def test_rejeita_bytes_que_nao_comecam_com_grib(self):
        with pytest.raises(GfsWaveParseError, match="não é um arquivo GRIB2"):
            parse_gfswave_grib2(b"nao e grib", COPACABANA)

    def test_extrai_todas_as_variaveis_esperadas(self):
        # shortNames reais confirmados contra uma resposta de verdade do NOMADS.
        mock_messages = [
            ("swh", 1.38), ("dirpw", 154.65), ("perpw", 10.53), ("ws", 3.51), ("wdir", 63.53),
        ]
        short_names = {i: name for i, (name, _) in enumerate(mock_messages)}

        with patch("eccodes.codes_grib_new_from_file") as mock_new, \
             patch("eccodes.codes_get") as mock_get, \
             patch("eccodes.codes_grib_find_nearest") as mock_nearest, \
             patch("eccodes.codes_release"):
            mock_new.side_effect = [i for i in range(len(mock_messages))] + [None]
            mock_get.side_effect = _codes_get_side_effect(short_names)
            # cada ponto vizinho é um candidato válido (não é o sentinela)
            mock_nearest.side_effect = [
                [MagicMock(value=value), MagicMock(value=MISSING_VALUE),
                 MagicMock(value=MISSING_VALUE), MagicMock(value=MISSING_VALUE)]
                for _, value in mock_messages
            ]

            result = parse_gfswave_grib2(FAKE_GRIB2_BYTES, COPACABANA)

        assert result == {"swh": 1.38, "dirpw": 154.65, "perpw": 10.53, "ws": 3.51, "wdir": 63.53}

    def test_levanta_erro_quando_nenhuma_variavel_esperada_e_encontrada(self):
        with patch("eccodes.codes_grib_new_from_file") as mock_new, \
             patch("eccodes.codes_get") as mock_get, \
             patch("eccodes.codes_grib_find_nearest") as mock_nearest, \
             patch("eccodes.codes_release"):
            mock_new.side_effect = [0, None]
            mock_get.side_effect = _codes_get_side_effect({0: "variavel_irrelevante"})
            mock_nearest.side_effect = [[MagicMock(value=42.0)]]

            with pytest.raises(GfsWaveParseError, match="dados insuficientes"):
                parse_gfswave_grib2(FAKE_GRIB2_BYTES, COPACABANA)

    def test_pula_ponto_mais_proximo_quando_e_terra_e_usa_o_proximo_valido(self):
        # Recreio/Grumari/Prainha: o ponto de grade mais próximo cai em terra
        # (valor sentinela 9999), mas o 2º ou 3º mais próximo tem dado real.
        with patch("eccodes.codes_grib_new_from_file") as mock_new, \
             patch("eccodes.codes_get") as mock_get, \
             patch("eccodes.codes_grib_find_nearest") as mock_nearest, \
             patch("eccodes.codes_release"):
            mock_new.side_effect = [0, None]
            mock_get.side_effect = _codes_get_side_effect({0: "swh"})
            mock_nearest.side_effect = [[
                MagicMock(value=MISSING_VALUE),  # mais próximo: terra
                MagicMock(value=MISSING_VALUE),  # 2º mais próximo: terra
                MagicMock(value=1.2),            # 3º mais próximo: mar, válido
                MagicMock(value=1.5),
            ]]

            result = parse_gfswave_grib2(FAKE_GRIB2_BYTES, COPACABANA)

        assert result == {"swh": 1.2}

    def test_levanta_erro_quando_todos_os_pontos_vizinhos_sao_terra(self):
        with patch("eccodes.codes_grib_new_from_file") as mock_new, \
             patch("eccodes.codes_get") as mock_get, \
             patch("eccodes.codes_grib_find_nearest") as mock_nearest, \
             patch("eccodes.codes_release"):
            mock_new.side_effect = [0, None]
            mock_get.side_effect = _codes_get_side_effect({0: "swh"})
            mock_nearest.side_effect = [[MagicMock(value=MISSING_VALUE)] * 4]

            with pytest.raises(GfsWaveParseError, match="dados insuficientes"):
                parse_gfswave_grib2(FAKE_GRIB2_BYTES, COPACABANA)
