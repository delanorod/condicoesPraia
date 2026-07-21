"""Persistência via PostgreSQL + PostGIS.

Usa geografia (Point, SRID 4326) para as coordenadas das praias, permitindo
consultas espaciais nativas (ex.: "praia mais próxima de um ponto") via
ST_Distance / ST_DWithin, que o value object Coordinates.distance_to não
substitui em escala (Haversine em Python não usa índice espacial).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select

from app.domain.entities import Beach, CoastalCondition, WaveReading, WindReading
from app.domain.repositories import BeachRepository, CoastalConditionRepository
from app.domain.value_objects import Coordinates


class Base(DeclarativeBase):
    pass


class BeachModel(Base):
    __tablename__ = "beaches"

    id: str = Column(String, primary_key=True)
    name: str = Column(String, nullable=False)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)


class CoastalConditionModel(Base):
    __tablename__ = "coastal_conditions"

    id = Column(String, primary_key=True)
    beach_id: str = Column(String, nullable=False, index=True)
    observed_at: datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    wind_speed_ms: float = Column(Float, nullable=False)
    wind_gust_ms: float = Column(Float, nullable=False)
    wind_direction_deg: float = Column(Float, nullable=False)
    wave_height_m: float = Column(Float, nullable=False)
    wave_period_s: float = Column(Float, nullable=False)
    wave_direction_deg: float = Column(Float, nullable=False)
    sea_state: str = Column(String, nullable=False)


def _beach_from_model(model: BeachModel, latitude: float, longitude: float) -> Beach:
    return Beach(
        id=model.id,
        name=model.name,
        coordinates=Coordinates(latitude=latitude, longitude=longitude),
    )


class PostgisBeachRepository(BeachRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(self) -> list[Beach]:
        result = await self._session.execute(select(BeachModel))
        return [
            _beach_from_model(m, *self._extract_lat_lon(m)) for m in result.scalars().all()
        ]

    async def get_by_id(self, beach_id: str) -> Beach | None:
        result = await self._session.execute(select(BeachModel).where(BeachModel.id == beach_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _beach_from_model(model, *self._extract_lat_lon(model))

    @staticmethod
    def _extract_lat_lon(model: BeachModel) -> tuple[float, float]:
        # geoalchemy2 retorna WKB; em produção usar ST_X/ST_Y na query ou
        # to_shape() do shapely para extrair lat/lon do ponto armazenado.
        from geoalchemy2.shape import to_shape

        point = to_shape(model.location)
        return point.y, point.x  # (latitude, longitude)


class PostgisCoastalConditionRepository(CoastalConditionRepository):
    def __init__(self, session: AsyncSession, beach_repository: BeachRepository):
        self._session = session
        self._beach_repository = beach_repository

    async def save(self, condition: CoastalCondition) -> None:
        import uuid

        model = CoastalConditionModel(
            id=str(uuid.uuid4()),
            beach_id=condition.beach.id,
            observed_at=condition.wave.observed_at,
            wind_speed_ms=condition.wind.speed_ms,
            wind_gust_ms=condition.wind.gust_ms,
            wind_direction_deg=condition.wind.direction_deg,
            wave_height_m=condition.wave.height_m,
            wave_period_s=condition.wave.period_s,
            wave_direction_deg=condition.wave.direction_deg,
            sea_state=condition.sea_state.value,
        )
        self._session.add(model)
        await self._session.commit()

    async def get_latest_by_beach(self, beach_id: str) -> CoastalCondition | None:
        stmt = (
            select(CoastalConditionModel)
            .where(CoastalConditionModel.beach_id == beach_id)
            .order_by(CoastalConditionModel.observed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        beach = await self._beach_repository.get_by_id(beach_id)
        if beach is None:
            return None

        return CoastalCondition(
            beach=beach,
            wind=WindReading(
                speed_ms=model.wind_speed_ms,
                gust_ms=model.wind_gust_ms,
                direction_deg=model.wind_direction_deg,
                observed_at=model.observed_at,
            ),
            wave=WaveReading(
                height_m=model.wave_height_m,
                period_s=model.wave_period_s,
                direction_deg=model.wave_direction_deg,
                observed_at=model.observed_at,
            ),
        )
