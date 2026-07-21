"""Gera app/infrastructure/seed_beaches.py com TODAS as localidades do
estado do Rio de Janeiro listadas no praialimpa.net, geocodificadas via
Nominatim (OpenStreetMap, gratuito).

RODE ISSO UMA VEZ NA SUA MÁQUINA (não faz parte da suíte de testes, e não
roda no meu sandbox -- preciso de acesso à internet real ao praialimpa.net
e ao Nominatim, que meu ambiente de desenvolvimento não tem):

    python scripts/generate_beach_seed.py

Demora alguns minutos: o Nominatim pede no máximo 1 requisição/segundo, e
o site tem mais de 100 localidades distintas no estado inteiro.

Coordenadas geocodificadas automaticamente são APROXIMADAS -- Nominatim às
vezes acha o centro do bairro/cidade em vez do ponto exato da praia, o que
é aceitável para consultar o modelo de onda/vento (grade de 0.25 grau), mas
não para navegação de precisão. Localidades que o Nominatim não encontrar
ficam de fora e são listadas no final para você resolver manualmente se
quiser.
"""
import asyncio
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from app.infrastructure.nominatim_geocoder import NominatimGeocoder
from app.infrastructure.praia_limpa_client import PRAIA_LIMPA_URL, get_all_distinct_locations

OUTPUT_PATH = Path(__file__).parent.parent / "app" / "infrastructure" / "seed_beaches.py"

# O site agrupa alguns municípios sob rótulos compostos que não são um
# lugar geocodificável de verdade (ex: "Iguaba Grande e São Pedro
# d'Aldeia", "Região da Costa Verde (Mangaratiba e Itaguaí)"). Para a
# QUERY de geocodificação usamos o nome do município principal; o
# `municipality` salvo no Beach continua sendo o rótulo original do site
# (importante para o casamento com a balneabilidade continuar funcionando).
CITY_GEOCODING_HINTS = {
    "Casimiro de Abreu e Unamar (Cabo Frio)": "Casimiro de Abreu",
    "Iguaba Grande e São Pedro d'Aldeia": "Iguaba Grande",
    "Região da Costa Verde (Mangaratiba e Itaguaí)": "Mangaratiba",
    "Ilha do Governador e Ramos": "Ilha do Governador",
}


def _slugify(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", without_accents).strip("-").lower()
    return slug


async def main() -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Baixando {PRAIA_LIMPA_URL}...")
        response = await client.get(PRAIA_LIMPA_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        locations = get_all_distinct_locations(response.text)
        print(f"{len(locations)} localidades distintas encontradas no estado inteiro.\n")

        geocoder = NominatimGeocoder(http_client=client)
        beaches = []
        failures = []
        approximated = []

        for i, (city, name) in enumerate(locations, start=1):
            city_hint = CITY_GEOCODING_HINTS.get(city, city)
            query = f"Praia {name}, {city_hint}, Rio de Janeiro, Brasil"
            print(f"[{i}/{len(locations)}] {query} ...", end=" ")
            coords = await geocoder.geocode(query)
            if coords is None:
                # tenta sem o prefixo "Praia" -- alguns nomes de
                # município/bairro geocodificam melhor sem ele
                coords = await geocoder.geocode(f"{name}, {city_hint}, Rio de Janeiro, Brasil")

            is_approximated = False
            if coords is None:
                # último recurso: centro do município (impreciso, mas
                # melhor que não ter nenhum dado de onda/vento)
                coords = await geocoder.geocode(f"{city_hint}, Rio de Janeiro, Brasil")
                is_approximated = coords is not None

            if coords is None:
                print("NÃO ENCONTRADO")
                failures.append((city, name))
                continue

            slug = f"{_slugify(name)}-{_slugify(city)}"
            beaches.append((slug, name, city, coords.latitude, coords.longitude))
            if is_approximated:
                approximated.append((city, name))
                print(f"OK ({coords.latitude}, {coords.longitude}) -- aproximado, centro do município")
            else:
                print(f"OK ({coords.latitude}, {coords.longitude})")

    lines = [
        '"""Seed gerado automaticamente por scripts/generate_beach_seed.py',
        "a partir de TODAS as localidades do estado do RJ no praialimpa.net.",
        "Coordenadas via Nominatim/OpenStreetMap -- aproximadas, não exatas.",
        f'Gerado com {len(beaches)} de {len(locations)} localidades encontradas.',
        '"""',
        "from __future__ import annotations",
        "",
        "from app.domain.entities import Beach",
        "from app.domain.value_objects import Coordinates",
        "",
        "RIO_BEACHES: list[Beach] = [",
    ]
    for slug, name, city, lat, lon in beaches:
        name_escaped = name.replace('"', '\\"')
        city_escaped = city.replace('"', '\\"')
        lines.append(
            f'    Beach(id="{slug}", name="{name_escaped}", '
            f"coordinates=Coordinates(latitude={lat}, longitude={lon}), "
            f'municipality="{city_escaped}"),'
        )
    lines.append("]")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{len(beaches)} praias escritas em {OUTPUT_PATH}")
    if approximated:
        print(f"\n{len(approximated)} localidade(s) usaram coordenada APROXIMADA (centro do município,")
        print("não achou a praia específica -- ok pra onda/vento, mas o ponto no mapa não é exato):")
        for city, name in approximated:
            print(f"  - {name} ({city})")
    if failures:
        print(f"\n{len(failures)} localidade(s) NÃO geocodificada(s) -- ficaram de fora:")
        for city, name in failures:
            print(f"  - {name} ({city})")
        print("\nVocê pode adicionar essas manualmente depois, com coordenadas de outra fonte.")


if __name__ == "__main__":
    asyncio.run(main())
