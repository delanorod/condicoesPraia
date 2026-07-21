# API de Condições Costeiras — Praias do Rio de Janeiro

Vento e ondas em tempo real via **NOAA GFS-Wave (WAVEWATCH III)**, por praia,
construído com TDD (Red-Green-Refactor), Clean Architecture / DDD, FastAPI e
PostgreSQL+PostGIS.

> **Histórico de decisões sobre a fonte de dados** (relevante se você for
> mexer nisso depois):
> 1. NOAA NDBC (boias físicas) — **abandonado**: não cobre a costa do Rio.
> 2. Open-Meteo — funciona bem, mas a licença gratuita proíbe uso comercial
>    (app com anúncio/assinatura). Código ainda existe em
>    `app/infrastructure/open_meteo_client.py` como alternativa caso você
>    decida assinar o plano pago deles no futuro (mais simples que a opção
>    atual).
> 3. PacIOOS ERDDAP (redistribuição do WaveWatch III) — **abandonado**: a
>    licença é uma cortesia acadêmica ambígua, arriscada para app comercial.
> 4. **NOAA GFS-Wave direto via NOMADS (atual)** — domínio público, sem
>    ambiguidade. Trade-off: formato GRIB2, mais complexo de instalar e
>    processar que uma API JSON.
>
> **Status: confirmado e funcionando** ✅ — testado contra o servidor real
> do NOMADS em 15/07/2026. Os shortNames GRIB2 reais são `swh` (altura de
> onda), `dirpw` (direção de onda), `perpw` (período de onda), `ws`
> (velocidade do vento), `wdir` (direção do vento) — diferentes do que a
> documentação sugeria inicialmente (`htsgw`, `10ws`, `10wdir`), então fica
> o registro para quem for mexer nisso depois.
>
> ⚠️ **Gust (rajada de vento) não está disponível no GFS-Wave** — o campo
> `gust_ms` hoje é uma aproximação igual à velocidade do vento (`ws`). Se
> precisar de rajada de verdade, dá para buscar o campo `GUST` do produto
> GFS atmosférico principal (arquivo `gfs.tXXz.pgrb2.0p25.fXXX`, diretório
> `/gfs.{date}/{cycle}/atmos`) — é outra chamada HTTP, mas a mesma técnica.

## Rodando

```bash
pip install -r requirements.txt
python -m pytest --cov=app --cov-report=term-missing   # suíte de testes (não precisa de banco)
```

## Ligando ao Supabase (produção / app mobile)

> Usamos o **cliente Python oficial da Supabase** (fala HTTPS/REST, porta
> 443) em vez de conexão direta em Postgres — a conexão direta exige rede
> IPv6, que a maioria das redes domésticas/Windows não tem, e isso causava
> `ConnectionRefusedError`. Como consequência, trocamos o tipo de coluna
> geográfica do PostGIS por `latitude`/`longitude` simples — não estávamos
> usando consultas espaciais mesmo.

1. Crie um projeto em [supabase.com](https://supabase.com) (região São Paulo).
2. Pegue a URL e a chave em **Project Settings → Data API**:
   - `Project URL` → vai em `BEACH_API_SUPABASE_URL`
   - `service_role` key (não a `anon`) → vai em `BEACH_API_SUPABASE_KEY`.
     **Nunca exponha essa chave no app mobile** — ela só deve existir no seu
     backend/servidor. O app mobile fala com a *sua* API, não direto com a
     Supabase.
3. Copie `.env.example` para `.env` e preencha essas duas variáveis.
4. Cole o conteúdo de `schema.sql` no SQL Editor do Supabase e rode — cria
   as tabelas `beaches` e `coastal_conditions`.
5. Popule as praias no banco:
   ```
   python scripts/seed_beaches_to_db.py
   ```
6. Rode a coleta pela primeira vez (senão a API não tem nada para servir):
   ```
   python scripts/collect_daily_conditions.py
   ```
7. Suba a API:
   ```
   uvicorn app.infrastructure.api.main:app --reload
   ```
   `GET /praias/copacabana/condicoes` agora lê do Supabase — rápido, sem
   chamar a NOAA a cada requisição do app mobile.

**Agendando a coleta**: rode `scripts/collect_daily_conditions.py`
periodicamente (o GFS-Wave só publica ciclo novo a cada 6h, então 4x/dia é o
teto útil). Opções sem custo: Agendador de Tarefas do Windows, cron num
servidor Linux, ou GitHub Actions com gatilho `schedule` (não precisa manter
nenhum servidor rodando).

## Estrutura (Clean Architecture)

```
app/
  domain/            <- regras de negócio puras, zero dependências externas
    entities.py         Beach, WindReading, WaveReading, CoastalCondition, SeaState
    value_objects.py    Coordinates (imutável, com distância Haversine)
    repositories.py     Portas (interfaces): BeachRepository, OceanDataSource, ...
  application/        <- orquestração, sem lógica de negócio própria
    use_cases.py        GetCoastalConditionUseCase
    exceptions.py       BeachNotFoundError
  infrastructure/     <- detalhes: web, HTTP, banco de dados
    open_meteo_client.py Adapter Open-Meteo (Marine API + Weather API)
    postgis_repository.py   Implementação PostGIS das portas do domínio
    in_memory_beach_repository.py   Implementação simples (dev/testes)
    api/                 FastAPI: rotas, DTOs, injeção de dependências
```

**Regra de dependência**: `domain` não importa nada de `application` ou
`infrastructure`. `application` importa `domain`, nunca `infrastructure`
diretamente (apenas as interfaces/portas). `infrastructure` implementa as
portas do domínio e é o único lugar que sabe que existe FastAPI, HTTP,
SQLAlchemy ou PostGIS. Isso é o que permite trocar `InMemoryBeachRepository`
por `PostgisBeachRepository`, ou o NDBC por outra fonte de dados oceânicos,
sem tocar em `domain/` nem `application/`.

## Decisões de design

- **NOAA NDBC não tem API JSON.** Os dados "realtime2" são arquivos de texto
  (`data.ndbc.noaa.gov/data/realtime2/{station}.txt`), delimitados por espaço,
  com a leitura mais recente na primeira linha de dados. O parser
  (`parse_ndbc_realtime_text`) é uma função pura, testada isoladamente de
  qualquer chamada HTTP — é o tipo de código mais propenso a bugs sutis
  (formato mudou, campo ausente = `"MM"`), então ganhou a maior cobertura de
  casos de borda.
- **Classificação do estado do mar na entidade `WaveReading`**, não em um
  "service" solto: é comportamento que depende só dos dados da própria
  leitura de onda, então mora ali (tell, don't ask).
- **`asyncio.gather` para vento e onda em paralelo** no caso de uso: as duas
  chamadas ao NDBC são independentes, then paralelizar corta a latência
  observada pela metade sem adicionar complexidade real.
- **DTOs Pydantic vivem em `infrastructure/api/schemas.py`**, não no domínio.
  O domínio não deveria saber que existe serialização JSON ou nomes de campo
  em português para a API pública — são decisões de apresentação.
- **`Coordinates.distance_to` usa Haversine em Python**, adequado para poucas
  praias. Para "praia mais próxima" em escala, a versão PostGIS usa
  `ST_DWithin`/`ST_Distance` com índice `GIST`, que é o que justifica o uso de
  `GEOGRAPHY(POINT, 4326)` em vez de calcular tudo em Python.
- **Repositório em memória como padrão, PostGIS como opção de produção**: os
  testes de integração da API usam dublês (fakes) via
  `dependency_overrides` do FastAPI — nunca sobem um Postgres real. Isso é
  intencional: testes rápidos e determinísticos na esteira de CI. Testes
  contra o Postgres real (com Testcontainers, por exemplo) ficam para a
  seção de melhorias.

## Lista de testes priorizados (do mais simples ao mais complexo)

1. `Coordinates` — validação de faixa, imutabilidade, distância Haversine
2. `WaveReading` / `WindReading` — validação de invariantes (altura ≥ 0 etc.)
3. `SeaState` — classificação por limiares (aqui um teste pegou um bug real
   de fronteira `<` vs `<=` antes de chegar a produção)
4. `CoastalCondition` — agregação e regra `is_rough()`
5. Parser NDBC (`parse_ndbc_realtime_text`) — função pura, sem I/O
6. `NdbcOceanDataSource` — cliente HTTP com rede mockada (respx)
7. `GetCoastalConditionUseCase` — orquestração com repositórios fake
8. `InMemoryBeachRepository` — CRUD simples
9. Endpoints FastAPI (`/health`, `/praias`, `/praias/{id}/condicoes`) —
   `TestClient` + `dependency_overrides`
10. **(Não implementado ainda)** `PostgisBeachRepository` /
    `PostgisCoastalConditionRepository` contra banco real — requer
    Testcontainers ou banco de CI dedicado

## Cobertura atual

```
Domain (entities, value_objects, repositories):  100%
Application (use_cases, exceptions):              100%
Infrastructure/API (schemas, dependencies):        82-100%
Infrastructure (noaa_client, in_memory_repo):      98-100%
Infrastructure (postgis_repository, config):       0% — requer banco real
------------------------------------------------------------------
TOTAL:                                             74%
```

O núcleo do negócio (domínio + aplicação) está em 100%. O que falta é
código de infraestrutura que depende de um Postgres/PostGIS real —
propositalmente fora do escopo de testes unitários/mockados.

## Sugestões de melhoria contínua

1. **Testes de integração reais contra PostGIS** com [Testcontainers](https://testcontainers-python.readthedocs.io/)
   no CI, cobrindo `postgis_repository.py` (hoje 0%) sem depender de um banco
   fixo no ambiente de teste.
2. **Cache de curto prazo (Redis ou in-process com TTL)** para as respostas
   do NDBC — estações reportam a cada ~1h, então repetir a request a cada
   chamada da API é desperdício e aumenta risco de rate limiting da NOAA.
3. **Fallback quando a estação NDBC mais próxima não cobre a praia**: nem
   toda praia carioca tem uma boia física perto (ex. praias na Baía de
   Guanabara). Avaliar reanálise/modelo (ex. Copernicus Marine, como você já
   vinha explorando) como fonte secundária, com a mesma porta
   `OceanDataSource` — é só implementar outro adapter.
4. **Endpoint de série histórica** (`GET /praias/{id}/condicoes/historico`)
   usando `CoastalConditionRepository.get_latest_by_beach` e uma variante com
   janela de tempo — dado que o schema já persiste cada observação.
5. **Alertas de mar agitado** (`is_rough()` já existe no domínio): um job
   periódico que varre todas as praias e dispara notificação/webhook quando
   `sea_state` piora — reaproveitando a mesma lógica de domínio, sem
   duplicação.
6. **Autenticação/rate limiting na API pública**, se for exposta fora da
   rede interna do PUC-Rio.
7. **Testes de contrato para o parser NDBC**: gravar periodicamente uma
   resposta real do NDBC como fixture, para detectar quando a NOAA mudar o
   formato do arquivo `.txt` (já aconteceu historicamente).
8. Preencher `[Requisito 3]` do seu documento original — me diga o que era
   (histórico, alertas, cache, autenticação, outra fonte de dados?) que eu
   sigo com TDD do mesmo jeito.
