import pytest

from app.domain.entities import SeaState
from app.domain.scoring import sea_state_to_agitation


class TestSeaStateToAgitation:
    @pytest.mark.parametrize("sea_state,esperado", [
        (SeaState.CALMO, None),
        (SeaState.QUASE_CALMO, None),
        (SeaState.LEVE, None),
        (SeaState.MODERADO, "Moderado"),
        (SeaState.AGITADO, "Moderado"),
        (SeaState.MUITO_AGITADO, "Forte"),
        (SeaState.ALTO, "Forte"),
    ])
    def test_mapeia_estado_do_mar_para_agitacao(self, sea_state, esperado):
        assert sea_state_to_agitation(sea_state) == esperado
