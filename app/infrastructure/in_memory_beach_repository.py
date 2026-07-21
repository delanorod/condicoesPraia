from __future__ import annotations

from app.domain.entities import Beach
from app.domain.repositories import BeachRepository


class InMemoryBeachRepository(BeachRepository):
    """Implementação simples para desenvolvimento/testes. Troque por
    PostgisBeachRepository em produção sem alterar a camada de aplicação."""

    def __init__(self, beaches: list[Beach]):
        self._beaches = {beach.id: beach for beach in beaches}

    async def get_all(self) -> list[Beach]:
        return list(self._beaches.values())

    async def get_by_id(self, beach_id: str) -> Beach | None:
        return self._beaches.get(beach_id)
