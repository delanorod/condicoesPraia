"""Schemas de resposta HTTP. Ficam na borda (infraestrutura), não no domínio,
para que o domínio não dependa de Pydantic nem de detalhes de serialização."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.entities import CoastalCondition


class BeachDTO(BaseModel):
    id: str
    nome: str
    municipio: str
    bairro: str
    regiao: str
    latitude: float
    longitude: float


class WindDTO(BaseModel):
    velocidade_ms: float
    rajada_ms: float
    direcao_graus: float
    observado_em: datetime


class WaveDTO(BaseModel):
    altura_m: float
    periodo_s: float
    direcao_graus: float
    observado_em: datetime


class CoastalConditionDTO(BaseModel):
    praia: BeachDTO
    vento: WindDTO
    onda: WaveDTO
    estado_do_mar: str
    mar_agitado: bool

    @classmethod
    def from_domain(cls, condition: CoastalCondition) -> "CoastalConditionDTO":
        return cls(
            praia=BeachDTO(
                id=condition.beach.id,
                nome=condition.beach.name,
                municipio=condition.beach.municipality,
                bairro=condition.beach.neighborhood,
                regiao=condition.beach.region,
                latitude=condition.beach.coordinates.latitude,
                longitude=condition.beach.coordinates.longitude,
            ),
            vento=WindDTO(
                velocidade_ms=condition.wind.speed_ms,
                rajada_ms=condition.wind.gust_ms,
                direcao_graus=condition.wind.direction_deg,
                observado_em=condition.wind.observed_at,
            ),
            onda=WaveDTO(
                altura_m=condition.wave.height_m,
                periodo_s=condition.wave.period_s,
                direcao_graus=condition.wave.direction_deg,
                observado_em=condition.wave.observed_at,
            ),
            estado_do_mar=condition.sea_state.value,
            mar_agitado=condition.is_rough(),
        )
