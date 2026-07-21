"""Job de coleta de balneabilidade: busca no Praia Limpa (fonte: INEA) e salva.

Separado por completo do job de vento/onda (collect_daily_conditions.py) --
fonte, frequência e natureza do dado são diferentes.

Rode manualmente para testar:

    python scripts/collect_balneabilidade.py

Salva no Supabase E escreve um snapshot local `balneabilidade.json` (mesmo
formato que o fluxo antigo do usuário gerava), caso o app queira ler o
arquivo direto em vez de bater na API.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from supabase import acreate_client

from app.application.use_cases import RefreshBalneabilityUseCase
from app.config import settings
from app.infrastructure.praia_limpa_client import PraiaLimpaBalneabilityDataSource
from app.infrastructure.supabase_repository import SupabaseBalneabilityRepository, SupabaseBeachRepository

OUTPUT_JSON = Path(__file__).parent.parent / "balneabilidade.json"


async def main() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        beach_repository = SupabaseBeachRepository(client)
        balneability_repository = SupabaseBalneabilityRepository(client)
        data_source = PraiaLimpaBalneabilityDataSource(http_client)
        use_case = RefreshBalneabilityUseCase(beach_repository, data_source, balneability_repository)

        statuses = await use_case.execute()

    if not statuses:
        print("Nenhum status de balneabilidade encontrado -- confira se o site mudou de estrutura")
        print("(rode scripts/verificar_praia_limpa.py para diagnosticar).")
        return

    for beach_id, status in statuses.items():
        print(f"{beach_id}: {status.value}")

    snapshot = {
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "fonte": "INEA (via praialimpa.net)",
        "praias": {beach_id: status.value for beach_id, status in statuses.items()},
    }
    OUTPUT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(statuses)} praia(s) salvas no Supabase e em {OUTPUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
