from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from app.application.exceptions import BeachNotFoundError, NoStoredConditionError
from app.application.use_cases import GetStoredCoastalConditionUseCase
from app.infrastructure.api.dependencies import (
    get_balneability_repository,
    get_beach_repository,
    get_stored_coastal_condition_use_case,
)
from app.infrastructure.api.schemas import BeachDTO, CoastalConditionDTO

app = FastAPI(
    title="API de Condições Costeiras - Praias do Rio de Janeiro",
    description="Vento e ondas por praia carioca, via NOAA GFS-Wave, atualizado periodicamente.",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/praias", response_model=list[BeachDTO])
async def list_beaches(beach_repository=Depends(get_beach_repository)) -> list[BeachDTO]:
    beaches = await beach_repository.get_all()
    return [
        BeachDTO(id=b.id, nome=b.name, municipio=b.municipality, bairro=b.neighborhood, regiao=b.region,
                  latitude=b.coordinates.latitude, longitude=b.coordinates.longitude)
        for b in beaches
    ]


@app.get("/praias/{beach_id}/condicoes", response_model=CoastalConditionDTO)
async def get_coastal_condition(
    beach_id: str,
    use_case: GetStoredCoastalConditionUseCase = Depends(get_stored_coastal_condition_use_case),
) -> CoastalConditionDTO:
    """Devolve a última condição salva no banco (rápido — é o que o app mobile deve chamar).

    Os dados são atualizados por um job separado
    (`scripts/collect_daily_conditions.py`), não a cada chamada.
    """
    try:
        condition = await use_case.execute(beach_id)
    except BeachNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NoStoredConditionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CoastalConditionDTO.from_domain(condition)


@app.get("/praias/{beach_id}/balneabilidade")
async def get_balneability(
    beach_id: str,
    beach_repository=Depends(get_beach_repository),
    balneability_repository=Depends(get_balneability_repository),
) -> dict:
    """Endpoint separado do de condições: fonte (Praia Limpa/INEA), frequência
    e natureza do dado são diferentes de vento/onda."""
    beach = await beach_repository.get_by_id(beach_id)
    if beach is None:
        raise HTTPException(status_code=404, detail=f"praia não encontrada: {beach_id}")

    status = await balneability_repository.get_latest_by_beach(beach_id)
    if status is None:
        raise HTTPException(status_code=503, detail=f"balneabilidade ainda não coletada para: {beach_id}")

    return {"praia_id": beach_id, "balneabilidade": status.value}
