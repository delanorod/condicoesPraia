from app.domain.entities import Beach
from app.domain.value_objects import Coordinates
from app.infrastructure.praia_limpa_client import (
    BalneabilityStatus,
    aggregate_by_beach,
    match_to_known_beach,
    parse_balneabilidade_texts,
)

# Trecho REAL extraído do site (via fetch em 18/07/2026), incluindo a
# armadilha real: "Vermelha" aparece de novo na seção de Angra dos Reis com
# o mesmo nome de praia do Rio -- agora que capturamos o ESTADO inteiro,
# essa repetição é esperada e distinguida pela cidade, não descartada.
TEXTOS_REAIS = [
    "PraiaLimpa.net", "Rio de Janeiro", "Alagoas", "Ceará",
    "Oi, eu sou o Pedro! Me paga um café?", "Copiar Pix",
    "Rio de Janeiro",
    "Própria", "Arpoador", "Canto esquerdo da praia",
    "Própria", "Barra da Tijuca", "Em frente à Avenida Ayrton Senna",
    "Imprópria", "Barra da Tijuca", "Quebra-Mar - Em frente à Rua Sargento João de Faria",
    "Imprópria", "Copacabana", "Em frente à Rua Francisco Otaviano",
    "Própria", "Copacabana", "Em frente à Rua Santa Clara",
    "Imprópria", "Ipanema", "Em frente à Rua Paul Redefern",
    "Imprópria", "Ipanema", "Em frente à Rua Garcia D'Ávila",
    "n/a", "Ipanema", "Em frente à Rua Joana Angélica",
    "Própria", "Grumari", "Canto direito da praia",
    "Imprópria", "Grumari", "Centro da praia",
    "Própria", "Urca", "Centro da praia",
    "Imprópria", "Vermelha", "Centro da praia",
    "Atualizado em 08/07/2026",
    "Niterói",
    "Imprópria", "Adão", "Centro da praia",
    "Atualizado em 08/07/2026",
    "Angra dos Reis",
    "Própria", "Vermelha", "Lado direito da praia",  # mesmo nome, cidade diferente
    "Atualizado em 02/07/2026",
]

RIO_BEACHES_TESTE = [
    Beach(id="copacabana-rio-de-janeiro", name="Copacabana",
          coordinates=Coordinates(latitude=-22.9868, longitude=-43.1897), municipality="Rio de Janeiro"),
    Beach(id="ipanema-rio-de-janeiro", name="Ipanema",
          coordinates=Coordinates(latitude=-22.9868, longitude=-43.2044), municipality="Rio de Janeiro"),
    Beach(id="arpoador-rio-de-janeiro", name="Arpoador",
          coordinates=Coordinates(latitude=-22.9889, longitude=-43.1936), municipality="Rio de Janeiro"),
    Beach(id="barra-da-tijuca-rio-de-janeiro", name="Barra da Tijuca",
          coordinates=Coordinates(latitude=-23.0116, longitude=-43.3652), municipality="Rio de Janeiro"),
    Beach(id="grumari-rio-de-janeiro", name="Grumari",
          coordinates=Coordinates(latitude=-23.05333, longitude=-43.53500), municipality="Rio de Janeiro"),
    Beach(id="urca-rio-de-janeiro", name="Urca",
          coordinates=Coordinates(latitude=-22.9489, longitude=-43.1656), municipality="Rio de Janeiro"),
    Beach(id="vermelha-rio-de-janeiro", name="Vermelha",
          coordinates=Coordinates(latitude=-22.95528, longitude=-43.16472), municipality="Rio de Janeiro"),
    Beach(id="vermelha-angra-dos-reis", name="Vermelha",
          coordinates=Coordinates(latitude=-23.0, longitude=-44.3), municipality="Angra dos Reis"),
]


class TestParseBalneabilidadeTexts:
    def test_captura_entradas_de_todas_as_cidades_do_estado(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        cidades = {e.city for e in entradas}
        assert cidades == {"Rio de Janeiro", "Niterói", "Angra dos Reis"}

    def test_distingue_vermelha_do_rio_de_vermelha_de_angra_pela_cidade(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        vermelhas = {(e.city, e.status) for e in entradas if e.beach_name == "Vermelha"}
        assert vermelhas == {
            ("Rio de Janeiro", BalneabilityStatus.IMPROPRIA),
            ("Angra dos Reis", BalneabilityStatus.PROPRIA),
        }

    def test_trata_n_a_como_indisponivel_em_vez_de_perder_a_entrada(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        ipanema_na = [e for e in entradas if e.beach_name == "Ipanema" and e.status == BalneabilityStatus.INDISPONIVEL]
        assert len(ipanema_na) == 1

    def test_captura_multiplos_pontos_da_mesma_praia(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        barra = [e for e in entradas if e.beach_name == "Barra da Tijuca"]
        assert len(barra) == 2


class TestAggregateByBeach:
    def test_agrega_por_par_cidade_praia_nao_so_pelo_nome(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        agregados = aggregate_by_beach(entradas)
        assert agregados[("Rio de Janeiro", "Vermelha")] == BalneabilityStatus.IMPROPRIA
        assert agregados[("Angra dos Reis", "Vermelha")] == BalneabilityStatus.PROPRIA

    def test_impropria_vence_se_qualquer_ponto_estiver_impropio(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        agregados = aggregate_by_beach(entradas)
        assert agregados[("Rio de Janeiro", "Barra da Tijuca")] == BalneabilityStatus.IMPROPRIA
        assert agregados[("Rio de Janeiro", "Copacabana")] == BalneabilityStatus.IMPROPRIA

    def test_propria_quando_todos_os_pontos_sao_proprios(self):
        entradas = parse_balneabilidade_texts(TEXTOS_REAIS)
        agregados = aggregate_by_beach(entradas)
        assert agregados[("Rio de Janeiro", "Arpoador")] == BalneabilityStatus.PROPRIA
        assert agregados[("Rio de Janeiro", "Urca")] == BalneabilityStatus.PROPRIA


class TestMatchToKnownBeach:
    def test_casa_por_nome_e_cidade(self):
        beach = match_to_known_beach("Copacabana", "Rio de Janeiro", RIO_BEACHES_TESTE)
        assert beach.id == "copacabana-rio-de-janeiro"

    def test_nao_confunde_vermelha_do_rio_com_vermelha_de_angra(self):
        rio = match_to_known_beach("Vermelha", "Rio de Janeiro", RIO_BEACHES_TESTE)
        angra = match_to_known_beach("Vermelha", "Angra dos Reis", RIO_BEACHES_TESTE)
        assert rio.id == "vermelha-rio-de-janeiro"
        assert angra.id == "vermelha-angra-dos-reis"

    def test_casa_nome_abreviado_por_substring_dentro_da_mesma_cidade(self):
        recreio = Beach(id="recreio-dos-bandeirantes-rio-de-janeiro", name="Recreio dos Bandeirantes",
                         coordinates=Coordinates(latitude=-23.0264, longitude=-43.4649),
                         municipality="Rio de Janeiro")
        beach = match_to_known_beach("Recreio", "Rio de Janeiro", [*RIO_BEACHES_TESTE, recreio])
        assert beach.id == "recreio-dos-bandeirantes-rio-de-janeiro"

    def test_retorna_none_para_praia_desconhecida(self):
        beach = match_to_known_beach("Diabo", "Rio de Janeiro", RIO_BEACHES_TESTE)
        assert beach is None

    def test_retorna_none_quando_nome_existe_mas_em_outra_cidade(self):
        # "Arpoador" só existe cadastrado para o Rio; pedir em Niterói não deve casar.
        beach = match_to_known_beach("Arpoador", "Niterói", RIO_BEACHES_TESTE)
        assert beach is None
