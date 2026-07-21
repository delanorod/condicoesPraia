"""Converte o arquivo praias_rj.json (dado curado do usuário -- coordenadas
mais precisas que a geocodificação automática, com bairro/região) em
entidades Beach para o seed."""
from __future__ import annotations

import re
import unicodedata

from app.domain.entities import Beach
from app.domain.value_objects import Coordinates


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", without_accents).strip("-").lower()


def convert_praias_rj_json(data: dict) -> list[Beach]:
    beaches: list[Beach] = []
    for item in data.get("praias", []):
        lat, lon = item.get("lat"), item.get("lon")
        if lat is None or lon is None:
            continue

        name = item["nome"]
        municipality = item.get("municipio", "Rio de Janeiro")
        slug = f"{_slugify(name)}-{_slugify(municipality)}"

        beaches.append(Beach(
            id=slug,
            name=name,
            coordinates=Coordinates(latitude=lat, longitude=lon),
            municipality=municipality,
            neighborhood=item.get("bairro", "") or "",
            region=item.get("regiao", "") or "",
        ))
    return beaches
