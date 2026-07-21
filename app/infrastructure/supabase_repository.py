"""Adapters usando o cliente Python oficial da Supabase (fala HTTPS/REST via
PostgREST, porta 443) — evita o problema de conexão direta em Postgres exigir
IPv6 em muitas redes.

Schema esperado (ver schema.sql): tabelas `beaches` (id, name, latitude,
longitude) e `coastal_conditions` (leituras, uma linha por coleta).
"""
from __future__ import annotations

from datetime import datetime, timezone

from supabase import AsyncClient

from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.repositories import BeachRepository, CoastalConditionRepository
from app.domain.value_objects import Coordinates


def _row_to_beach(row: dict) -> Beach:
    return Beach(
        id=row["id"],
        name=row["name"],
        coordinates=Coordinates(latitude=row["latitude"], longitude=row["longitude"]),
        municipality=row.get("municipality", "Rio de Janeiro"),
        neighborhood=row.get("neighborhood", "") or "",
        region=row.get("region", "") or "",
    )


class SupabaseBeachRepository(BeachRepository):
    def __init__(self, client: AsyncClient):
        self._client = client

    async def get_all(self) -> list[Beach]:
        result = await self._client.table("beaches").select("*").execute()
        return [_row_to_beach(row) for row in result.data]

    async def get_by_id(self, beach_id: str) -> Beach | None:
        result = await self._client.table("beaches").select("*").eq("id", beach_id).execute()
        if not result.data:
            return None
        return _row_to_beach(result.data[0])


class SupabaseCoastalConditionRepository(CoastalConditionRepository):
    def __init__(self, client: AsyncClient, beach_repository: BeachRepository):
        self._client = client
        self._beach_repository = beach_repository

    async def save(self, condition: CoastalCondition) -> None:
        await self._client.table("coastal_conditions").insert({
            "beach_id": condition.beach.id,
            "observed_at": condition.wave.observed_at.isoformat(),
            "wind_speed_ms": condition.wind.speed_ms,
            "wind_gust_ms": condition.wind.gust_ms,
            "wind_direction_deg": condition.wind.direction_deg,
            "wave_height_m": condition.wave.height_m,
            "wave_period_s": condition.wave.period_s,
            "wave_direction_deg": condition.wave.direction_deg,
            "sea_state": condition.sea_state.value,
        }).execute()

    async def get_latest_by_beach(self, beach_id: str) -> CoastalCondition | None:
        result = (
            await self._client.table("coastal_conditions")
            .select("*")
            .eq("beach_id", beach_id)
            .order("observed_at", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]

        beach = await self._beach_repository.get_by_id(beach_id)
        if beach is None:
            return None

        observed_at = datetime.fromisoformat(row["observed_at"])
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        return CoastalCondition(
            beach=beach,
            wind=WindReading(
                speed_ms=row["wind_speed_ms"],
                gust_ms=row["wind_gust_ms"],
                direction_deg=row["wind_direction_deg"],
                observed_at=observed_at,
            ),
            wave=WaveReading(
                height_m=row["wave_height_m"],
                period_s=row["wave_period_s"],
                direction_deg=row["wave_direction_deg"],
                observed_at=observed_at,
            ),
        )


class SupabaseBalneabilityRepository:
    """Separado de CoastalConditionRepository de propósito: fonte, frequência
    e natureza do dado são diferentes (qualidade da água vs. vento/onda)."""

    def __init__(self, client):
        self._client = client

    async def save_all(self, statuses: dict) -> None:
        from datetime import datetime, timezone

        rows = [
            {"beach_id": beach_id, "status": status.value, "checked_at": datetime.now(timezone.utc).isoformat()}
            for beach_id, status in statuses.items()
        ]
        if rows:
            await self._client.table("balneability").upsert(rows, on_conflict="beach_id").execute()

    async def get_latest_by_beach(self, beach_id: str):
        from app.infrastructure.praia_limpa_client import BalneabilityStatus

        result = await self._client.table("balneability").select("*").eq("beach_id", beach_id).execute()
        if not result.data:
            return None
        return BalneabilityStatus(result.data[0]["status"])
