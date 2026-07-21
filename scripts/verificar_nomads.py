"""Script de verificação manual — RODE ISSO NA SUA MÁQUINA, não faz parte da suíte de testes.

Este script existe porque o ambiente onde o código foi escrito não tem acesso
de rede ao NOMADS, então a integração real nunca foi confirmada. Rode:

    python scripts/verificar_nomads.py

E veja se aparece "SUCESSO" no final ou uma mensagem de erro explicando o que
ajustar (nome de parâmetro errado, variável GRIB2 com nome diferente do
esperado, etc.).
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from app.domain.value_objects import Coordinates
from app.infrastructure.noaa_gfswave_client import (
    build_gfswave_grib_filter_url,
    candidate_cycles,
    parse_gfswave_grib2,
)

COPACABANA = Coordinates(latitude=-22.9868, longitude=-43.1897)


async def main() -> None:
    now = datetime.now(timezone.utc)
    cycles = candidate_cycles(now)
    print(f"Vou tentar {len(cycles)} ciclos, do mais recente ao mais antigo:")
    for c in cycles:
        print(f"  - {c.isoformat()} UTC")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for cycle in cycles:
            url = build_gfswave_grib_filter_url(cycle, COPACABANA)
            print(f"Tentando ciclo {cycle.isoformat()} UTC...")
            print(f"URL: {url}")
            response = await client.get(url)
            print(f"Status HTTP: {response.status_code}")

            if response.status_code == 404:
                print("  -> ainda não publicado, tentando o ciclo anterior...\n")
                continue

            if response.status_code != 200:
                print(f"\nFALHOU: status inesperado. Corpo (primeiros 500 chars):")
                print(response.text[:500])
                return

            if not response.content.startswith(b"GRIB"):
                print("\nFALHOU: a resposta não começa com os bytes mágicos 'GRIB'.")
                print("Isso normalmente significa que os parâmetros da URL estão errados.")
                print("Primeiros 500 bytes da resposta:")
                print(response.content[:500])
                return

            print(f"Tamanho da resposta: {len(response.content)} bytes")
            print("\nA resposta é um GRIB2 válido. Tentando decodificar...")
            try:
                values = parse_gfswave_grib2(response.content, COPACABANA)
                print(f"\nSUCESSO com o ciclo {cycle.isoformat()}. Valores extraídos: {values}")
            except Exception as exc:
                print(f"\nFALHOU ao decodificar com eccodes: {exc}")
                print("Isso pode ser um nome de variável (shortName) diferente do esperado.")
            return

        print("\nNenhum dos ciclos tentados está disponível ainda. Tente novamente mais tarde,")
        print("ou aumente max_attempts em candidate_cycles().")


if __name__ == "__main__":
    asyncio.run(main())
