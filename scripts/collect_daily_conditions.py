"""Job de coleta: busca condições ao vivo na NOAA para cada praia e salva no Supabase.

Rode manualmente para testar:

    python scripts/collect_daily_conditions.py

Em produção, agende isso periodicamente (o GFS-Wave só publica ciclo novo a
cada 6h, então 4x/dia é o teto útil). Formas de agendar sem custo:
  - Windows: Agendador de Tarefas (Task Scheduler)
  - GitHub Actions com gatilho "schedule" (não precisa deixar o PC ligado)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from supabase import acreate_client

from app.application.exceptions import BeachNotFoundError
from app.application.use_cases import GetCoastalConditionUseCase
from app.config import settings
from app.infrastructure.noaa_gfswave_client import GfsWaveOceanDataSource
from app.infrastructure.supabase_repository import SupabaseBeachRepository, SupabaseCoastalConditionRepository


async def main() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        beach_repository = SupabaseBeachRepository(client)
        condition_repository = SupabaseCoastalConditionRepository(client, beach_repository=beach_repository)
        ocean_data_source = GfsWaveOceanDataSource(http_client=http_client)
        use_case = GetCoastalConditionUseCase(beach_repository, ocean_data_source)

        beaches = await beach_repository.get_all()
        if not beaches:
            print("Nenhuma praia cadastrada no banco. Rode scripts/seed_beaches_to_db.py primeiro.")
            return

        print(f"Coletando condições para {len(beaches)} praia(s)...\n")
        sucessos, falhas = 0, 0
        for beach in beaches:
            try:
                condition = await use_case.execute(beach.id)
                await condition_repository.save(condition)
                print(
                    f"OK: {beach.name} — onda {condition.wave.height_m:.2f}m, "
                    f"vento {condition.wind.speed_ms:.1f}m/s, mar {condition.sea_state.value}"
                )
                sucessos += 1
            except BeachNotFoundError:
                print(f"FALHOU: {beach.name} — praia não encontrada (inconsistência de dados)")
                falhas += 1
            except Exception as exc:  # noqa: BLE001 — uma praia falhar não deve parar as outras
                print(f"FALHOU: {beach.name} — {exc}")
                falhas += 1

    print(f"\nConcluído: {sucessos} sucesso(s), {falhas} falha(s).")


if __name__ == "__main__":
    asyncio.run(main())
