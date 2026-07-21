"""Seed gerado a partir de praias_rj.json (dado curado pelo usuário --
coordenadas mais precisas que geocodificação automática, com bairro/região).
Cobre Rio de Janeiro e Niterói. Para o restante do estado, rode
scripts/generate_beach_seed.py e mescle manualmente, ou peça ajuda.
"""
from __future__ import annotations

from app.domain.entities import Beach
from app.domain.value_objects import Coordinates

RIO_BEACHES: list[Beach] = [
    Beach(id="gragoata-niteroi", name="Gragoatá", coordinates=Coordinates(latitude=-22.895, longitude=-43.123), municipality="Niterói", neighborhood="São Domingos", region="Niterói"),
    Beach(id="leme-rio-de-janeiro", name="Leme", coordinates=Coordinates(latitude=-22.9635, longitude=-43.1674), municipality="Rio de Janeiro", neighborhood="Leme", region="Zona Sul"),
    Beach(id="pepino-rio-de-janeiro", name="Pepino", coordinates=Coordinates(latitude=-23.007, longitude=-43.282), municipality="Rio de Janeiro", neighborhood="São Conrado", region="Zona Sul"),
    Beach(id="vermelha-rio-de-janeiro", name="Vermelha", coordinates=Coordinates(latitude=-22.9533, longitude=-43.1607), municipality="Rio de Janeiro", neighborhood="Urca", region="Zona Sul"),
    Beach(id="recreio-dos-bandeirantes-rio-de-janeiro", name="Recreio dos Bandeirantes", coordinates=Coordinates(latitude=-23.0241, longitude=-43.4626), municipality="Rio de Janeiro", neighborhood="Recreio dos Bandeirantes", region="Zona Oeste"),
    Beach(id="prainha-rio-de-janeiro", name="Prainha", coordinates=Coordinates(latitude=-23.0415, longitude=-43.5043), municipality="Rio de Janeiro", neighborhood="Recreio dos Bandeirantes", region="Zona Oeste"),
    Beach(id="grumari-rio-de-janeiro", name="Grumari", coordinates=Coordinates(latitude=-23.0548, longitude=-43.5283), municipality="Rio de Janeiro", neighborhood="Grumari", region="Zona Oeste"),
    Beach(id="pontal-de-sernambetiba-rio-de-janeiro", name="Pontal de Sernambetiba", coordinates=Coordinates(latitude=-23.018, longitude=-43.445), municipality="Rio de Janeiro", neighborhood="Recreio dos Bandeirantes", region="Zona Oeste"),
    Beach(id="barra-de-guaratiba-rio-de-janeiro", name="Barra de Guaratiba", coordinates=Coordinates(latitude=-23.065, longitude=-43.57), municipality="Rio de Janeiro", neighborhood="Guaratiba", region="Zona Oeste"),
    Beach(id="camboinhas-niteroi", name="Camboinhas", coordinates=Coordinates(latitude=-22.9645, longitude=-43.0534), municipality="Niterói", neighborhood="Camboinhas", region="Niterói"),
    Beach(id="itaipu-niteroi", name="Itaipu", coordinates=Coordinates(latitude=-22.9591, longitude=-43.0493), municipality="Niterói", neighborhood="Itaipu", region="Niterói"),
    Beach(id="piratininga-niteroi", name="Piratininga", coordinates=Coordinates(latitude=-22.9554, longitude=-43.0588), municipality="Niterói", neighborhood="Piratininga", region="Niterói"),
    Beach(id="arpoador-rio-de-janeiro", name="Arpoador", coordinates=Coordinates(latitude=-22.9876, longitude=-43.194), municipality="Rio de Janeiro", neighborhood="Ipanema", region="Zona Sul"),
    Beach(id="diabo-rio-de-janeiro", name="Diabo", coordinates=Coordinates(latitude=-22.988, longitude=-43.196), municipality="Rio de Janeiro", neighborhood="Ipanema", region="Zona Sul"),
    Beach(id="itacoatiara-niteroi", name="Itacoatiara", coordinates=Coordinates(latitude=-22.9681, longitude=-43.0356), municipality="Niterói", neighborhood="Itacoatiara", region="Niterói"),
    Beach(id="macumba-rio-de-janeiro", name="Macumba", coordinates=Coordinates(latitude=-23.031, longitude=-43.4921), municipality="Rio de Janeiro", neighborhood="Recreio dos Bandeirantes", region="Zona Oeste"),
    Beach(id="joatinga-rio-de-janeiro", name="Joatinga", coordinates=Coordinates(latitude=-23.0102, longitude=-43.2879), municipality="Rio de Janeiro", neighborhood="Joá", region="Zona Sul"),
    Beach(id="icarai-niteroi", name="Icaraí", coordinates=Coordinates(latitude=-22.9035, longitude=-43.1106), municipality="Niterói", neighborhood="Icaraí", region="Niterói"),
    Beach(id="boa-viagem-niteroi", name="Boa Viagem", coordinates=Coordinates(latitude=-22.899, longitude=-43.115), municipality="Niterói", neighborhood="Boa Viagem", region="Niterói"),
    Beach(id="sao-francisco-niteroi", name="São Francisco", coordinates=Coordinates(latitude=-22.915, longitude=-43.118), municipality="Niterói", neighborhood="São Francisco", region="Niterói"),
    Beach(id="copacabana-rio-de-janeiro", name="Copacabana", coordinates=Coordinates(latitude=-22.9711, longitude=-43.1823), municipality="Rio de Janeiro", neighborhood="Copacabana", region="Zona Sul"),
    Beach(id="sao-conrado-rio-de-janeiro", name="São Conrado", coordinates=Coordinates(latitude=-23.0038, longitude=-43.2753), municipality="Rio de Janeiro", neighborhood="São Conrado", region="Zona Sul"),
    Beach(id="flamengo-rio-de-janeiro", name="Flamengo", coordinates=Coordinates(latitude=-22.9295, longitude=-43.1736), municipality="Rio de Janeiro", neighborhood="Flamengo", region="Zona Sul"),
    Beach(id="botafogo-rio-de-janeiro", name="Botafogo", coordinates=Coordinates(latitude=-22.9519, longitude=-43.182), municipality="Rio de Janeiro", neighborhood="Botafogo", region="Zona Sul"),
    Beach(id="urca-rio-de-janeiro", name="Urca", coordinates=Coordinates(latitude=-22.9486, longitude=-43.1637), municipality="Rio de Janeiro", neighborhood="Urca", region="Zona Sul"),
    Beach(id="barra-da-tijuca-rio-de-janeiro", name="Barra da Tijuca", coordinates=Coordinates(latitude=-23.0048, longitude=-43.3658), municipality="Rio de Janeiro", neighborhood="Barra da Tijuca", region="Zona Oeste"),
    Beach(id="charitas-niteroi", name="Charitas", coordinates=Coordinates(latitude=-22.9231, longitude=-43.12), municipality="Niterói", neighborhood="Charitas", region="Niterói"),
    Beach(id="jurujuba-niteroi", name="Jurujuba", coordinates=Coordinates(latitude=-22.9354, longitude=-43.1118), municipality="Niterói", neighborhood="Jurujuba", region="Niterói"),
    Beach(id="ipanema-rio-de-janeiro", name="Ipanema", coordinates=Coordinates(latitude=-22.9868, longitude=-43.204), municipality="Rio de Janeiro", neighborhood="Ipanema", region="Zona Sul"),
    Beach(id="leblon-rio-de-janeiro", name="Leblon", coordinates=Coordinates(latitude=-22.9877, longitude=-43.223), municipality="Rio de Janeiro", neighborhood="Leblon", region="Zona Sul"),
    Beach(id="vidigal-rio-de-janeiro", name="Vidigal", coordinates=Coordinates(latitude=-22.9932, longitude=-43.2349), municipality="Rio de Janeiro", neighborhood="Vidigal", region="Zona Sul"),
    Beach(id="gloria-rio-de-janeiro", name="Glória", coordinates=Coordinates(latitude=-22.9232, longitude=-43.174), municipality="Rio de Janeiro", neighborhood="Glória", region="Zona Sul"),
]
