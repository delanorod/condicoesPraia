"""Script de verificação manual -- RODE ISSO NA SUA MÁQUINA, não faz parte da suíte de testes.

O parser de app/infrastructure/praia_limpa_client.py foi testado com uma
fixture baseada num trecho REAL do site (capturado em 18/07/2026), mas o
site pode mudar. Rode isto pra conferir rapidamente:

    python scripts/verificar_praia_limpa.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from app.infrastructure.praia_limpa_client import PRAIA_LIMPA_URL, parse_balneabilidade_html
from app.infrastructure.seed_beaches import RIO_BEACHES


async def main() -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Baixando {PRAIA_LIMPA_URL}...")
        response = await client.get(PRAIA_LIMPA_URL, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Status HTTP: {response.status_code}\n")

        if response.status_code != 200:
            print("FALHOU: status inesperado.")
            return

        result = parse_balneabilidade_html(response.text, RIO_BEACHES)

        if not result:
            print("FALHOU: nenhuma praia foi reconhecida.")
            print("Isso normalmente significa que a estrutura do site mudou")
            print("(nomes de status diferentes, ou o marcador 'Atualizado em' sumiu).")
            return

        print(f"SUCESSO: {len(result)} de {len(RIO_BEACHES)} praias reconhecidas:\n")
        for beach in RIO_BEACHES:
            status = result.get(beach.id, "(não encontrada)")
            print(f"  {beach.id:15} {status}")

        nao_encontradas = [b.id for b in RIO_BEACHES if b.id not in result]
        if nao_encontradas:
            print(f"\nAtenção: {len(nao_encontradas)} praia(s) não apareceram no site: {nao_encontradas}")
            print("(pode ser normal -- nem toda praia tem monitoramento do INEA)")


if __name__ == "__main__":
    asyncio.run(main())
