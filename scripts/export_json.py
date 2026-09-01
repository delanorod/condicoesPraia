"""
Exporta onda/vento + balneabilidade + score de recomendação de TODAS as
praias num único JSON estático (condicoes.json), mantendo compatibilidade
com o formato anteriormente utilizado pelo aplicativo Flutter.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import acreate_client

from app.application.exceptions import (
    BeachNotFoundError,
    NoStoredConditionError,
)
from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.config import settings
from app.domain.scoring import calculate_beach_score, classify_agitation
from app.domain.value_objects import mps_to_kmh
from app.infrastructure.supabase_repository import (
    SupabaseBalneabilityRepository,
    SupabaseBeachRepository,
    SupabaseCoastalConditionRepository,
)


OUTPUT_JSON = Path(__file__).parent.parent / "condicoes.json"


async def main() -> None:
    client = await acreate_client(
        settings.supabase_url,
        settings.supabase_key,
    )

    beach_repository = SupabaseBeachRepository(client)

    condition_repository = SupabaseCoastalConditionRepository(
        client,
        beach_repository=beach_repository,
    )

    balneability_repository = SupabaseBalneabilityRepository(client)

    use_case = GetStoredCoastalConditionUseCase(
        beach_repository,
        condition_repository,
    )

    beaches = await beach_repository.get_all()

    print(f"Exportando {len(beaches)} praia(s)...")

    # Agora é uma LISTA, compatível com o antigo praias_rj.json
    praias_json = []

    # Guardaremos também a relação ID -> praia
    # apenas para descobrir corretamente a recomendada.
    praias_por_id = {}

    for beach in beaches:

        # Estrutura compatível com o Flutter antigo
        entry = {
            "nome": beach.name,
            "municipio": beach.municipality,
            "bairro": beach.neighborhood,
            "regiao": beach.region,
            "caracteristicas": list(beach.characteristics),

            "lat": beach.coordinates.latitude,

            # IMPORTANTE:
            # antigo JSON usava "lon", não "long"
            "lon": beach.coordinates.longitude,

            # Valores simples, como no JSON antigo
            "onda": None,
            "vento": None,

            "agitacao": None,
            "direcao": None,
            "periodo": None,

            "estado_do_mar": None,
            "observado_em": None,

            "balneabilidade": None,
            "score": 0,
        }

        wave_height_m = None
        wind_speed_kmh = None
        agitation = None

        try:
            condition = await use_case.execute(beach.id)

            wave_height_m = condition.wave.height_m

            wind_speed_kmh = mps_to_kmh(
                condition.wind.speed_ms
            )

            agitation = classify_agitation(
                wave_height_m
            )

            # ==========================================
            # FORMATO SIMPLES PARA COMPATIBILIDADE
            # ==========================================

            # Antes:
            # "vento": {
            #     "velocidade_kmh": ...
            # }
            #
            # Agora:
            entry["vento"] = wind_speed_kmh

            # Antes:
            # "onda": {
            #     "altura_m": ...
            # }
            #
            # Agora:
            entry["onda"] = wave_height_m

            # Dados adicionais úteis
            entry["direcao"] = condition.wave.direction_deg
            entry["periodo"] = condition.wave.period_s

            entry["estado_do_mar"] = (
                condition.sea_state.value
            )

            entry["agitacao"] = agitation

            entry["observado_em"] = (
                condition.wave.observed_at.isoformat()
            )

        except (
            BeachNotFoundError,
            NoStoredConditionError,
        ):
            pass

        # ==========================================
        # BALNEABILIDADE
        # ==========================================

        balneabilidade = (
            await balneability_repository
            .get_latest_by_beach(beach.id)
        )

        balneability_value = (
            balneabilidade.value
            if balneabilidade
            else None
        )

        entry["balneabilidade"] = balneability_value

        # ==========================================
        # SCORE
        # ==========================================

        entry["score"] = calculate_beach_score(
            wave_height_m=wave_height_m,
            wind_speed_kmh=wind_speed_kmh,
            agitation=agitation,
            balneability=balneability_value,
            characteristics=list(beach.characteristics),
        )

        # Lista para o JSON final
        praias_json.append(entry)

        # Mapa interno apenas para localizar a recomendada
        praias_por_id[beach.id] = entry


    # ==========================================
    # ESCOLHER PRAIA RECOMENDADA
    # ==========================================

    # Apenas praias PRÓPRIAS podem ser recomendadas.
    proprias = [
        (beach_id, entry)
        for beach_id, entry in praias_por_id.items()
        if entry["balneabilidade"] == "propria"
    ]

    # IMPORTANTE:
    # Se não houver praias próprias, não recomenda
    # nenhuma praia imprópria.
    candidatas = proprias

    familiares = [
        (beach_id, entry)
        for beach_id, entry in candidatas
        if "familiar" in entry["caracteristicas"]
    ]

    if familiares:
        candidatas = familiares

    # Descobre a praia recomendada
    if candidatas:

        praia_recomendada_id, praia_recomendada_entry = max(
            candidatas,
            key=lambda item: item[1]["score"],
        )

        # MUITO IMPORTANTE:
        # Exportamos o NOME da praia, e não o ID.
        praia_recomendada = (
            praia_recomendada_entry["nome"]
        )

    else:
        praia_recomendada = None


    # ==========================================
    # JSON FINAL
    # ==========================================

    output = {
        # Mantém o nome usado pelo JSON antigo
        "ultima_atualizacao": (
            datetime.now(timezone.utc).isoformat()
        ),

        "fonte_ondas": "NOAA GFS-Wave",

        "fonte_balneabilidade": (
            "INEA (via praialimpa.net)"
        ),

        # Agora contém o NOME da praia
        "praia_recomendada": praia_recomendada,

        # Agora é uma LISTA []
        "praias": praias_json,
    }


    # ==========================================
    # GRAVAR ARQUIVO
    # ==========================================

    OUTPUT_JSON.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Escrito em {OUTPUT_JSON} "
        f"({len(praias_json)} praias)"
    )

    if praia_recomendada:
        print(
            f"Praia recomendada hoje: "
            f"{praia_recomendada}"
        )
    else:
        print(
            "Nenhuma praia própria disponível "
            "para recomendação."
        )


if __name__ == "__main__":
    asyncio.run(main())