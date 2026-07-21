"""Popula a tabela `beaches` no Supabase com as praias de app/infrastructure/seed_beaches.py.

Rode isso UMA VEZ (ou de novo sempre que atualizar seed_beaches.py):

    python scripts/seed_beaches_to_db.py

Pré-requisito: já ter rodado schema.sql no SQL Editor do Supabase.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import acreate_client

from app.config import settings
from app.infrastructure.seed_beaches import RIO_BEACHES


async def main() -> None:
    client = await acreate_client(settings.supabase_url, settings.supabase_key)

    rows = [
        {"id": b.id, "name": b.name, "municipality": b.municipality,
         "neighborhood": b.neighborhood, "region": b.region,
         "latitude": b.coordinates.latitude, "longitude": b.coordinates.longitude}
        for b in RIO_BEACHES
    ]
    result = await client.table("beaches").upsert(rows).execute()

    for row in result.data:
        print(f"OK: {row['id']} ({row['name']})")
    print(f"\n{len(result.data)} praia(s) inserida(s)/atualizada(s).")


if __name__ == "__main__":
    asyncio.run(main())
