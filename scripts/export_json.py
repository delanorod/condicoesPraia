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

# ---------------------------------------------------------------------------
# Enriquecimento: direção em texto + fallback de bairro/região
# ---------------------------------------------------------------------------

_PONTOS_CARDEAIS = [
    "Norte", "Nordeste", "Leste", "Sudeste",
    "Sul", "Sudoeste", "Oeste", "Noroeste",
]


def graus_para_direcao(graus: float | None) -> str | None:
    """Converte graus (0-360) no ponto cardeal em português (8 direções)."""
    if graus is None:
        return None
    graus = float(graus) % 360
    indice = int((graus + 22.5) // 45) % 8
    return _PONTOS_CARDEAIS[indice]


# Macrorregião por município, usada quando o cadastro da praia (Supabase)
# não tem "region" preenchido. São "regiões turísticas" informais -- ajuste
# livremente caso o projeto adote outra nomenclatura.
REGIAO_POR_MUNICIPIO = {
    "Niterói": "Niterói",
    "Angra dos Reis": "Costa Verde",
    "Paraty": "Costa Verde",
    "Conceição de Jacareí": "Costa Verde",
    "Região da Costa Verde (Mangaratiba e Itaguaí)": "Costa Verde",
    "Búzios": "Região dos Lagos",
    "Cabo Frio": "Região dos Lagos",
    "Arraial do Cabo": "Região dos Lagos",
    "Araruama": "Região dos Lagos",
    "Saquarema": "Região dos Lagos",
    "Iguaba Grande e São Pedro d'Aldeia": "Região dos Lagos",
    "Casimiro de Abreu e Unamar (Cabo Frio)": "Região dos Lagos",
    "Maricá": "Região dos Lagos",
    "Macaé": "Costa do Sol",
    "Rio das Ostras": "Costa do Sol",
    "Campos": "Norte Fluminense",
    "São Francisco de Itabapoana": "Norte Fluminense",
    "São João da Barra": "Norte Fluminense",
    "Paquetá": "Baía de Guanabara",
    "Ilha do Governador e Ramos": "Baía de Guanabara",
}

# Bairro/região por nome de praia, só usado para o município "Rio de
# Janeiro" -- lá o município sozinho não diferencia Zona Sul de Zona Oeste,
# então é preciso saber o bairro. Chaves em minúsculas.
NOME_PARA_BAIRRO_REGIAO_RJ = {
    "barra da tijuca": ("Barra da Tijuca", "Zona Oeste"),
    "recreio dos bandeirantes": ("Recreio dos Bandeirantes", "Zona Oeste"),
    "recreio": ("Recreio dos Bandeirantes", "Zona Oeste"),
    "grumari": ("Grumari", "Zona Oeste"),
    "prainha": ("Recreio dos Bandeirantes", "Zona Oeste"),
    "macumba": ("Recreio dos Bandeirantes", "Zona Oeste"),
    "barra de guaratiba": ("Guaratiba", "Zona Oeste"),
    "pontal de sernambetiba": ("Recreio dos Bandeirantes", "Zona Oeste"),
    "copacabana": ("Copacabana", "Zona Sul"),
    "ipanema": ("Ipanema", "Zona Sul"),
    "leblon": ("Leblon", "Zona Sul"),
    "leme": ("Leme", "Zona Sul"),
    "arpoador": ("Ipanema", "Zona Sul"),
    "diabo": ("Ipanema", "Zona Sul"),
    "vidigal": ("Vidigal", "Zona Sul"),
    "são conrado": ("São Conrado", "Zona Sul"),
    "pepino": ("São Conrado", "Zona Sul"),
    "joatinga": ("Joá", "Zona Sul"),
    "flamengo": ("Flamengo", "Zona Sul"),
    "botafogo": ("Botafogo", "Zona Sul"),
    "urca": ("Urca", "Zona Sul"),
    "vermelha": ("Urca", "Zona Sul"),
    "glória": ("Glória", "Zona Sul"),
}


def preencher_bairro_regiao(entry: dict) -> None:
    """Preenche 'bairro'/'regiao' em branco direto no dict de saída."""
    if not entry.get("bairro") or not entry.get("regiao"):
        if entry["municipio"] == "Rio de Janeiro":
            info = NOME_PARA_BAIRRO_REGIAO_RJ.get(entry["nome"].strip().lower())
            if info:
                bairro, regiao = info
                entry["bairro"] = entry.get("bairro") or bairro
                entry["regiao"] = entry.get("regiao") or regiao
        if not entry.get("regiao"):
            regiao_municipio = REGIAO_POR_MUNICIPIO.get(entry["municipio"])
            if regiao_municipio:
                entry["regiao"] = regiao_municipio


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
        preencher_bairro_regiao(entry)

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
            # "direcao_graus" guarda o valor bruto em graus;
            # "direcao" passa a ser o ponto cardeal em português,
            # mais útil para exibir no app.
            entry["direcao_graus"] = condition.wave.direction_deg
            entry["direcao"] = graus_para_direcao(
                condition.wave.direction_deg
            )
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