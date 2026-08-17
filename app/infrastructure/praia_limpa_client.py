"""Adapter para o Praia Limpa (praialimpa.net), fonte pública de
balneabilidade (dado original: INEA) de todo o litoral do estado do Rio de
Janeiro.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

import httpx
from bs4 import BeautifulSoup

from app.domain.entities import Beach

PRAIA_LIMPA_URL = "https://praialimpa.net/"
# Fonte oficial (referência apenas -- bloqueia acesso automatizado via
# robots.txt, então não construímos scraper para ela; ver observação no
# módulo). Mantida aqui só para citar como `url_inea` nos registros.
INEA_BALNEABILIDADE_URL = "https://www.inea.rj.gov.br/ar-agua-e-solo/balneabilidade-das-praias/"
MAX_IDADE_DIAS = 21


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
    updated_at_text: str | None = None  # texto bruto de "Atualizado em DD/MM/YYYY"


def parse_balneabilidade_texts(texts: list[str]) -> list[BalneabilityEntry]:
    """Recebe a lista de nós de texto da página e devolve as entradas
    (cidade, praia, status, data) de TODOS os municípios, na ordem em que
    aparecem.

    SUPOSIÇÃO NÃO CONFIRMADA: assumimos que 'Atualizado em DD/MM/YYYY'
    funciona como CABEÇALHO da seção seguinte (a data vale para a cidade
    que vem depois dele no texto). É igualmente plausível que seja RODAPÉ
    da seção anterior. Não dá para confirmar isso só pela ordem do texto
    extraído (BeautifulSoup ignora a estrutura visual de blocos/colunas).
    Se `data_coleta` parecer sistematicamente "adiantada" ou "atrasada" em
    relação ao que o site mostra visualmente, essa é a primeira suspeita.
    """
    entries: list[BalneabilityEntry] = []
    current_city: str | None = None
    current_updated_at: str | None = None
    status_atual: BalneabilityStatus | None = None
    expecting_city_header = False

    for raw in texts:
        t = raw.strip()
        if not t:
            continue

        if t.startswith("Atualizado em"):
            expecting_city_header = True
            current_updated_at = t.replace("Atualizado em", "").strip()
            continue

        if expecting_city_header:
            current_city = t
            expecting_city_header = False
            continue

        lowered = t.lower()
        if lowered in _STATUS_WORDS:
            status_atual = _STATUS_WORDS[lowered]
            continue

        if status_atual is not None:
            if current_city is not None:
                entries.append(BalneabilityEntry(
                    city=current_city, beach_name=t, status=status_atual,
                    updated_at_text=current_updated_at,
                ))
            status_atual = None
            continue

        if current_city is None and t == "Rio de Janeiro":
            current_city = t

    return entries


def aggregate_by_beach(entries: list[BalneabilityEntry]) -> dict[tuple[str, str], BalneabilityEntry]:
    severity = {BalneabilityStatus.PROPRIA: 0, BalneabilityStatus.INDISPONIVEL: 1, BalneabilityStatus.IMPROPRIA: 2}
    result: dict[tuple[str, str], BalneabilityEntry] = {}
    for entry in entries:
        key = (entry.city, entry.beach_name)
        current = result.get(key)
        if current is None or severity[entry.status] > severity[current.status]:
            result[key] = entry
    return result


def _normalize(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return without_accents.strip().lower()


def match_to_known_beach(scraped_name: str, city: str, known_beaches: list[Beach]) -> Beach | None:
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
    soup = BeautifulSoup(html, "html.parser")
    texts = soup.find_all(string=True)
    entries = parse_balneabilidade_texts(list(texts))
    aggregated = aggregate_by_beach(entries)

    result: dict[str, BalneabilityStatus] = {}
    for (city, scraped_name), entry in aggregated.items():
        beach = match_to_known_beach(scraped_name, city, known_beaches)
        if beach is not None:
            result[beach.id] = entry.status
    return result


class PraiaLimpaBalneabilityDataSource:
    def __init__(self, http_client: httpx.AsyncClient):
        self._http_client = http_client

    async def fetch_all(self, known_beaches: list[Beach]) -> dict[str, BalneabilityStatus]:
        response = await self._http_client.get(PRAIA_LIMPA_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return parse_balneabilidade_html(response.text, known_beaches)

    async def fetch_all_detailed(self, known_beaches: list[Beach]) -> list["BalneabilidadeData"]:
        """Igual a fetch_all, mas devolve o formato rico (BalneabilidadeData)
        em vez do dict simples -- aditivo, não substitui fetch_all (usado
        pelo pipeline já em produção) para que a transição seja suave."""
        response = await self._http_client.get(PRAIA_LIMPA_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        texts = soup.find_all(string=True)
        entries = parse_balneabilidade_texts(list(texts))
        aggregated = aggregate_by_beach(entries)

        today = datetime.now().date()
        resultados: list[BalneabilidadeData] = []
        for (city, scraped_name), entry in aggregated.items():
            beach = match_to_known_beach(scraped_name, city, known_beaches)
            if beach is not None:
                resultados.append(build_balneabilidade_data(beach, entry, today=today))
        return resultados


@dataclass
class BalneabilidadeData:
    """Estrutura de balneabilidade compatível com inea_scraper2.py, para uma
    transição suave entre o pipeline antigo (open-meteo + praialimpa.net
    direto) e o atual (NOAA GFS-Wave + Supabase)."""
    praia_id: str
    praia_nome: str
    status: str  # 'propria' | 'impropria' | 'indisponivel'
    coliformes_fecais: int | None
    data_coleta: str | None  # formato: YYYY-MM-DD
    municipio: str
    regiao: str
    coordenadas: dict | None
    bairro: str = ""
    extensao_km: float | None = None
    caracteristicas: list[str] = field(default_factory=list)
    fonte: str = "INEA"
    observacoes: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    url_inea: str | None = INEA_BALNEABILIDADE_URL


def parse_update_date(texto: str) -> date | None:
    """Extrai uma data DD/MM/YYYY de um texto (ex: '08/07/2026'). Devolve
    None se não encontrar/não conseguir interpretar."""
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", texto)
    if not match:
        return None
    dia, mes, ano = match.groups()
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def build_balneabilidade_data(
    beach: Beach, entry: BalneabilityEntry, today: date,
) -> BalneabilidadeData:
    """Combina metadados da praia (cadastro) com o status coletado,
    aplicando a regra de MAX_IDADE_DIAS: dado mais velho que isso vira
    'indisponivel' em vez de reportar um status que pode estar defasado."""
    status = entry.status.value
    observacoes = None
    data_coleta_iso = None

    data_coleta = parse_update_date(entry.updated_at_text) if entry.updated_at_text else None
    if data_coleta is not None:
        data_coleta_iso = data_coleta.isoformat()
        idade_dias = (today - data_coleta).days
        if idade_dias > MAX_IDADE_DIAS:
            status = BalneabilityStatus.INDISPONIVEL.value
            observacoes = f"Dado desatualizado ({idade_dias} dias sem atualização, limite é {MAX_IDADE_DIAS})"

    return BalneabilidadeData(
        praia_id=beach.id,
        praia_nome=beach.name,
        status=status,
        coliformes_fecais=None,  # não disponível via scraping do praialimpa.net
        data_coleta=data_coleta_iso,
        municipio=beach.municipality,
        regiao=beach.region,
        coordenadas={"latitude": beach.coordinates.latitude, "longitude": beach.coordinates.longitude},
        bairro=beach.neighborhood,
        extensao_km=None,
        caracteristicas=list(getattr(beach, "characteristics", ())),
        fonte="INEA",
        observacoes=observacoes,
        url_inea=INEA_BALNEABILIDADE_URL,
    )