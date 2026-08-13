"""Score de recomendação de praia -- pontuação heurística combinando onda,
vento, agitação e balneabilidade. Lógica e limiares replicados exatamente
do script original do usuário (gerar_json_praias.py::calcular_score).

Domínio puro: recebe primitivos (float/str), não depende de infraestrutura
nem de nenhum outro módulo -- pode ser usado tanto pela API quanto por
scripts de exportação (ex: scripts/export_json.py).
"""
from __future__ import annotations


def classify_agitation(wave_height_m: float) -> str:
    """Classifica agitação diretamente pela altura da onda -- replica
    exatamente extrator_ondasZSul.py::classificar_agitacao. Note que isso é
    INDEPENDENTE do nosso SeaState (escala Douglas, 7 níveis): são duas
    classificações diferentes, com limiares próprios, mantidas separadas."""
    if wave_height_m < 0.5:
        return "Fraco"
    if wave_height_m < 1.25:
        return "Moderado"
    if wave_height_m < 2.5:
        return "Forte"
    return "Muito Forte"


_TAGS_NAO_FAMILIAR = frozenset({"surf", "selvagem", "mergulho", "kite", "rochosa"})


def calculate_beach_score(
    wave_height_m: float | None,
    wind_speed_kmh: float | None,
    agitation: str | None,
    balneability: str | None,
    characteristics: list[str] | None = None,
) -> int:
    score = 0

    if balneability == "propria":
        score += 100
    elif balneability == "impropria":
        score -= 100

    if wave_height_m is not None:
        if wave_height_m < 0.5:
            score += 40
        elif wave_height_m < 1.0:
            score += 30
        elif wave_height_m < 1.5:
            score += 10
        else:
            score -= 10

    if wind_speed_kmh is not None:
        if wind_speed_kmh < 10:
            score += 30
        elif wind_speed_kmh < 20:
            score += 15
        elif wind_speed_kmh > 30:
            score -= 20

    if agitation == "Forte":
        score -= 20
    elif agitation == "Moderado":
        score -= 5

    if characteristics:
        if "familiar" in characteristics:
            score += 25
        if any(tag in _TAGS_NAO_FAMILIAR for tag in characteristics):
            score -= 15

    return score
