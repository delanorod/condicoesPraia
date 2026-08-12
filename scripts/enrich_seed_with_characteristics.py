"""Enriquece app/infrastructure/seed_beaches.py com as 'characteristics'
(familiar, surf, tranquila, etc) do cadastro curado do INEA
(inea_scraper2.py::INEAScraper.PRAIAS), casando por NOME + MUNICÍPIO
(nunca só pelo nome -- praias homônimas existem em municípios diferentes,
ex: "Vermelha" no Rio E em Angra dos Reis, "Prainha" em 3 lugares).

Pré-requisito: Beach precisa ter o campo `characteristics: tuple[str, ...] = ()`
em app/domain/entities.py (ver patch enviado separadamente).

Rode uma vez:

    python scripts/enrich_seed_with_characteristics.py
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.seed_beaches import RIO_BEACHES

SEED_PATH = Path(__file__).parent.parent / "app" / "infrastructure" / "seed_beaches.py"

# Cadastro curado (Rio de Janeiro + Niterói), extraído de inea_scraper2.py.
# Chave: (nome normalizado, município normalizado) -> tags.
REGISTRO = {
    ("leme", "rio de janeiro"): ["urbanizada", "familiar"],
    ("copacabana", "rio de janeiro"): ["urbanizada", "turística"],
    ("arpoador", "rio de janeiro"): ["surf", "pôr-do-sol"],
    ("ipanema", "rio de janeiro"): ["urbanizada", "turística"],
    ("leblon", "rio de janeiro"): ["urbanizada", "nobre"],
    ("vidigal", "rio de janeiro"): ["pequena", "pitoresca"],
    ("sao conrado", "rio de janeiro"): ["surf", "tranquila"],
    ("joatinga", "rio de janeiro"): ["secreta", "bela"],
    ("pepino", "rio de janeiro"): ["asa-delta", "tranquila"],
    ("diabo", "rio de janeiro"): ["pequena", "rochosa"],
    ("flamengo", "rio de janeiro"): ["baía", "esporte"],
    ("botafogo", "rio de janeiro"): ["baía", "histórica"],
    ("urca", "rio de janeiro"): ["tranquila", "baía"],
    ("vermelha", "rio de janeiro"): ["pequena", "mergulho"],
    ("gloria", "rio de janeiro"): ["baía", "histórica"],
    ("barra da tijuca", "rio de janeiro"): ["surf", "maior-praia"],
    ("recreio dos bandeirantes", "rio de janeiro"): ["familiar", "tranquila"],
    ("recreio", "rio de janeiro"): ["familiar", "tranquila"],
    ("macumba", "rio de janeiro"): ["surf", "jovem"],
    ("prainha", "rio de janeiro"): ["surf", "preservada"],
    ("grumari", "rio de janeiro"): ["APA", "selvagem"],
    ("pontal de sernambetiba", "rio de janeiro"): ["tranquila"],
    ("pontal", "rio de janeiro"): ["tranquila"],
    ("barra de guaratiba", "rio de janeiro"): ["pesca", "tranquila"],
    ("icarai", "niterói"): ["urbanizada", "familiar"],
    ("charitas", "niterói"): ["baía", "calma"],
    ("jurujuba", "niterói"): ["pesca", "baía"],
    ("camboinhas", "niterói"): ["tranquila"],
    ("itacoatiara", "niterói"): ["surf", "rochosa"],
    ("itaipu", "niterói"): ["pesca", "surf"],
    ("piratininga", "niterói"): ["lagoa", "kite"],
    ("gragoata", "niterói"): ["baía", "pequena"],
    ("boa viagem", "niterói"): ["baía", "ilha"],
    ("sao francisco", "niterói"): ["baía"],
}


def normalize(s: str) -> str:
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip().lower()


def main() -> None:
    casadas = 0
    linhas_saida = [
        '"""Seed enriquecido com características do cadastro do INEA',
        '(rode scripts/generate_beach_seed.py de novo para atualizar coordenadas;',
        'rode scripts/enrich_seed_with_characteristics.py de novo para reaplicar tags)."""',
        "from __future__ import annotations",
        "",
        "from app.domain.entities import Beach",
        "from app.domain.value_objects import Coordinates",
        "",
        "RIO_BEACHES: list[Beach] = [",
    ]

    for beach in RIO_BEACHES:
        chave = (normalize(beach.name), normalize(beach.municipality))
        tags = REGISTRO.get(chave)

        name_esc = beach.name.replace('"', '\\"')
        muni_esc = beach.municipality.replace('"', '\\"')
        neigh_esc = beach.neighborhood.replace('"', '\\"')
        region_esc = beach.region.replace('"', '\\"')

        if tags:
            casadas += 1
            tags_str = ", ".join(f'"{t}"' for t in tags)
            characteristics_str = f'({tags_str},)'
        else:
            characteristics_str = "()"

        linhas_saida.append(
            f'    Beach(id="{beach.id}", name="{name_esc}", '
            f"coordinates=Coordinates(latitude={beach.coordinates.latitude}, longitude={beach.coordinates.longitude}), "
            f'municipality="{muni_esc}", neighborhood="{neigh_esc}", region="{region_esc}", '
            f'characteristics={characteristics_str}),'
        )

    linhas_saida.append("]")

    SEED_PATH.write_text("\n".join(linhas_saida) + "\n", encoding="utf-8")
    print(f"{casadas} praias enriquecidas com características (de {len(REGISTRO)} no cadastro)")
    print(f"Escrito em {SEED_PATH}")


if __name__ == "__main__":
    main()
