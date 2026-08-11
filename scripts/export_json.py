"""Exporta onda/vento + balneabilidade de TODAS as praias num único JSON
estático (condicoes.json), pronto para servir direto (GitHub Pages,
raw.githubusercontent.com, ou qualquer hospedagem de arquivo estático) --
sem precisar de servidor rodando.

Rode depois de collect_daily_conditions.py e collect_balneabilidade.py:

    python scripts/export_json.py
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import acreate_client

from app.application.exceptions import BeachNotFoundError, NoStoredConditionError
from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.config import settings
from app.infrastructure.supabase_repository import (
    SupabaseBalneabilityRepository,
    SupabaseBeachRepository,
    SupabaseCoastalConditionRepository,
)

OUTPUT_JSON = Path(__file__).parent.parent / "condicoes.json"


async def main() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)

    beach_repository = SupabaseBeachRepository(client)
    condition_repository = SupabaseCoastalConditionRepository(client, beach_repository=beach_repository)
    balneability_repository = SupabaseBalneabilityRepository(client)
    use_case = GetStoredCoastalConditionUseCase(beach_repository, condition_repository)

    beaches = await beach_repository.get_all()
    print(f"Exportando {len(beaches)} praia(s)...")

    praias_json = {}
    for beach in beaches:
        entry: dict = {
            "nome": beach.name,
            "municipio": beach.municipality,
            "bairro": beach.neighborhood,
            "regiao": beach.region,
            "latitude": beach.coordinates.latitude,
            "longitude": beach.coordinates.longitude,
        }

        try:
            condition = await use_case.execute(beach.id)
            entry["vento"] = {
                "velocidade_ms": condition.wind.speed_ms,
                "rajada_ms": condition.wind.gust_ms,
                "direcao_graus": condition.wind.direction_deg,
            }
            entry["onda"] = {
                "altura_m": condition.wave.height_m,
                "periodo_s": condition.wave.period_s,
                "direcao_graus": condition.wave.direction_deg,
            }
            entry["estado_do_mar"] = condition.sea_state.value
            entry["observado_em"] = condition.wave.observed_at.isoformat()
        except (BeachNotFoundError, NoStoredConditionError):
            entry["vento"] = None
            entry["onda"] = None
            entry["estado_do_mar"] = None
            entry["observado_em"] = None

        balneabilidade = await balneability_repository.get_latest_by_beach(beach.id)
        entry["balneabilidade"] = balneabilidade.value if balneabilidade else None

        praias_json[beach.id] = entry

    output = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "fonte_onda_vento": "NOAA GFS-Wave",
        "fonte_balneabilidade": "INEA (via praialimpa.net)",
        "praias": praias_json,
    }

    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Escrito em {OUTPUT_JSON} ({len(praias_json)} praias)")


"""Exporta onda/vento + balneabilidade + score de recomendação de TODAS as
praias num único JSON estático (condicoes.json), pronto para servir direto
(GitHub Pages, raw.githubusercontent.com, ou qualquer hospedagem de arquivo
estático) -- sem precisar de servidor rodando.

Rode depois de collect_daily_conditions.py e collect_balneabilidade.py:

    python scripts/export_json.py
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import acreate_client

from app.application.exceptions import BeachNotFoundError, NoStoredConditionError
from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.config import settings
from app.domain.scoring import calculate_beach_score, sea_state_to_agitation
from app.domain.value_objects import mps_to_kmh
from app.infrastructure.supabase_repository import (
    SupabaseBalneabilityRepository,
    SupabaseBeachRepository,
    SupabaseCoastalConditionRepository,
)

OUTPUT_JSON = Path(__file__).parent.parent / "condicoes.json"


async def main() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)

    beach_repository = SupabaseBeachRepository(client)
    condition_repository = SupabaseCoastalConditionRepository(client, beach_repository=beach_repository)
    balneability_repository = SupabaseBalneabilityRepository(client)
    use_case = GetStoredCoastalConditionUseCase(beach_repository, condition_repository)

    beaches = await beach_repository.get_all()
    print(f"Exportando {len(beaches)} praia(s)...")

    praias_json = {}
    for beach in beaches:
        entry: dict = {
            "id": beach.id,
            "nome": beach.name,
            "municipio": beach.municipality,
            "bairro": beach.neighborhood,
            "regiao": beach.region,
            "latitude": beach.coordinates.latitude,
            "longitude": beach.coordinates.longitude,
        }

        wave_height_m = None
        wind_speed_kmh = None
        agitation = None

        try:
            condition = await use_case.execute(beach.id)
            wave_height_m = condition.wave.height_m
            wind_speed_kmh = mps_to_kmh(condition.wind.speed_ms)
            agitation = sea_state_to_agitation(condition.sea_state)

            entry["vento"] = {
                "velocidade_kmh": wind_speed_kmh,
                "rajada_kmh": mps_to_kmh(condition.wind.gust_ms),
                "direcao_graus": condition.wind.direction_deg,
            }
            entry["onda"] = {
                "altura_m": wave_height_m,
                "periodo_s": condition.wave.period_s,
                "direcao_graus": condition.wave.direction_deg,
            }
            entry["estado_do_mar"] = condition.sea_state.value
            entry["agitacao"] = agitation
            entry["observado_em"] = condition.wave.observed_at.isoformat()
        except (BeachNotFoundError, NoStoredConditionError):
            entry["vento"] = None
            entry["onda"] = None
            entry["estado_do_mar"] = None
            entry["agitacao"] = None
            entry["observado_em"] = None

        balneabilidade = await balneability_repository.get_latest_by_beach(beach.id)
        balneability_value = balneabilidade.value if balneabilidade else None
        entry["balneabilidade"] = balneability_value

        entry["score"] = calculate_beach_score(
            wave_height_m=wave_height_m,
            wind_speed_kmh=wind_speed_kmh,
            agitation=agitation,
            balneability=balneability_value,
        )

        praias_json[beach.id] = entry

    # Praia recomendada do dia -- REGRA 1 (inegociável): praia com
    # balneabilidade imprópria NUNCA é recomendada, nem como último recurso.
    # Preferência: própria > sem dado de balneabilidade (None) > nunca imprópria.
    nao_impropria = [(bid, e) for bid, e in praias_json.items() if e["balneabilidade"] != "impropria"]
    proprias = [(bid, e) for bid, e in nao_impropria if e["balneabilidade"] == "propria"]
    candidatas = proprias if proprias else nao_impropria
    praia_recomendada = max(candidatas, key=lambda item: item[1]["score"])[0] if candidatas else None

    output = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "fonte_onda_vento": "NOAA GFS-Wave",
        "fonte_balneabilidade": "INEA (via praialimpa.net)",
        "praia_recomendada": praia_recomendada,
        "praias": list(praias_json.values()),  # lista, não objeto -- compatível com o app
    }

    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Escrito em {OUTPUT_JSON} ({len(praias_json)} praias)")
    if praia_recomendada:
        print(f"Praia recomendada hoje: {praias_json[praia_recomendada]['nome']} "
              f"(score {praias_json[praia_recomendada]['score']})")
    else:
        print("Nenhuma praia recomendável hoje (todas impróprias ou sem dado).")


if __name__ == "__main__":
    asyncio.run(main())
