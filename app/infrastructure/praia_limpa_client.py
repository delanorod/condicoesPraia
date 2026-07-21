"""Adapter para o Praia Limpa (praialimpa.net), fonte pública de
balneabilidade (dado original: INEA) de todo o litoral do estado do Rio de
Janeiro -- Rio de Janeiro (capital), Niterói, Angra dos Reis, Búzios, Cabo
Frio, Paraty, Macaé, Maricá, Saquarema, e outros ~20 municípios.

O site não tem API -- é HTML solto, texto sequencial sem estrutura clara por
tag. Nomes de praia se repetem entre municípios (ex: "Vermelha" existe no
Rio E em Angra dos Reis; "Prainha" existe em pelo menos 3 lugares), então o
parser rastreia explicitamente em qual seção de cidade está (usando a linha
"Atualizado em ..." como marcador de fim de seção -- o texto seguinte a ela
é sempre o nome do próximo município) e toda praia é identificada pelo par
(cidade, nome), nunca só pelo nome.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum

import httpx
from bs4 import BeautifulSoup

from app.domain.entities import Beach

PRAIA_LIMPA_URL = "https://praialimpa.net/"


class BalneabilityStatus(str, Enum):
    PROPRIA = "propria"
    IMPROPRIA = "impropria"
    INDISPONIVEL = "indisponivel"


_STATUS_WORDS = {
    "própria": BalneabilityStatus.PROPRIA,
    "imprópria": BalneabilityStatus.IMPROPRIA,
    "n/a": BalneabilityStatus.INDISPONIVEL,
}


@dataclass(frozen=True)
class BalneabilityEntry:
    city: str
    beach_name: str
    status: BalneabilityStatus


def parse_balneabilidade_texts(texts: list[str]) -> list[BalneabilityEntry]:
    """Recebe a lista de nós de texto da página (ex: soup.find_all(string=True))
    e devolve as entradas (cidade, praia, status) de TODOS os municípios, na
    ordem em que aparecem.
    """
    entries: list[BalneabilityEntry] = []
    current_city: str | None = None
    status_atual: BalneabilityStatus | None = None
    expecting_city_header = False
    previous_text: str | None = None

    for raw in texts:
        t = raw.strip()
        if not t:
            continue

        if t.startswith("Atualizado em"):
            expecting_city_header = True
            previous_text = t
            continue

        if expecting_city_header:
            current_city = t
            expecting_city_header = False
            previous_text = t
            continue

        lowered = t.lower()
        if lowered in _STATUS_WORDS:
            if current_city is None and previous_text is not None:
                # primeira seção da página: não há "Atualizado em" antes dela,
                # então o nome da cidade é o texto imediatamente anterior à
                # primeira palavra de status encontrada.
                current_city = previous_text
            status_atual = _STATUS_WORDS[lowered]
            previous_text = t
            continue

        if status_atual is not None:
            if current_city is not None:
                entries.append(BalneabilityEntry(city=current_city, beach_name=t, status=status_atual))
            status_atual = None
            previous_text = t
            continue

        previous_text = t

    return entries


def aggregate_by_beach(entries: list[BalneabilityEntry]) -> dict[tuple[str, str], BalneabilityStatus]:
    """Uma praia pode ter vários pontos de monitoramento. Política: pior
    status vence (impropria > indisponivel > propria) -- mais seguro para
    quem for decidir se entra no mar. Chave é (cidade, nome) -- nunca só o
    nome, porque nomes se repetem entre municípios."""
    severity = {BalneabilityStatus.PROPRIA: 0, BalneabilityStatus.INDISPONIVEL: 1, BalneabilityStatus.IMPROPRIA: 2}
    result: dict[tuple[str, str], BalneabilityStatus] = {}
    for entry in entries:
        key = (entry.city, entry.beach_name)
        current = result.get(key)
        if current is None or severity[entry.status] > severity[current]:
            result[key] = entry.status
    return result


def _normalize(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def match_to_known_beach(scraped_name: str, city: str, known_beaches: list[Beach]) -> Beach | None:
    """Casa por cidade (exata, normalizada) E nome (exato ou substring nos
    dois sentidos) -- nunca só pelo nome, para não confundir praias
    homônimas de municípios diferentes."""
    normalized_city = _normalize(city)
    normalized_scraped = _normalize(scraped_name)
    for beach in known_beaches:
        if _normalize(beach.municipality) != normalized_city:
            continue
        normalized_known = _normalize(beach.name)
        if normalized_scraped == normalized_known:
            return beach
        if normalized_scraped in normalized_known or normalized_known in normalized_scraped:
            return beach
    return None


def get_all_distinct_locations(html: str) -> list[tuple[str, str]]:
    """Extrai todos os pares (cidade, nome_da_praia) distintos do site,
    de TODOS os municípios -- usado pelo script de geração do seed
    (scripts/generate_beach_seed.py) para saber o que geocodificar."""
    soup = BeautifulSoup(html, "html.parser")
    texts = soup.find_all(string=True)
    entries = parse_balneabilidade_texts(list(texts))
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for entry in entries:
        key = (entry.city, entry.beach_name)
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def parse_balneabilidade_html(html: str, known_beaches: list[Beach]) -> dict[str, BalneabilityStatus]:
    """Pipeline completo: HTML -> texto -> entradas -> agregado -> mapeado por beach_id."""
    soup = BeautifulSoup(html, "html.parser")
    texts = soup.find_all(string=True)
    entries = parse_balneabilidade_texts(list(texts))
    aggregated = aggregate_by_beach(entries)

    result: dict[str, BalneabilityStatus] = {}
    for (city, scraped_name), status in aggregated.items():
        beach = match_to_known_beach(scraped_name, city, known_beaches)
        if beach is not None:
            result[beach.id] = status
    return result


class PraiaLimpaBalneabilityDataSource:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def fetch_all(self, known_beaches: list[Beach]) -> dict[str, BalneabilityStatus]:
        response = await self._http_client.get(PRAIA_LIMPA_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return parse_balneabilidade_html(response.text, known_beaches)
