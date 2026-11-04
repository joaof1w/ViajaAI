"""Carga inicial do banco: catálogo de interesses e acervo de lugares."""
from backend.extensions import db
from backend.models.interesse import Interesse
from backend.models.lugar import Lugar

INTERESSES = [
    {"slug": "praia", "nome": "Praia", "icone": "🌊", "cor": "#e6f4fb"},
    {"slug": "gastronomia", "nome": "Gastronomia", "icone": "🍽️", "cor": "#ffece4"},
    {"slug": "aventura", "nome": "Aventura", "icone": "🏔️", "cor": "#e7f6ec"},
    {"slug": "cultura", "nome": "Cultura", "icone": "🏛️", "cor": "#efe9fb"},
    {"slug": "museus", "nome": "Museus", "icone": "🖼️", "cor": "#fdf3d9"},
    {"slug": "natureza", "nome": "Natureza", "icone": "🌿", "cor": "#e6f6f0"},
]

IMAGENS = {
    "praia": "card-praia.svg",
    "gastronomia": "card-gastronomia.svg",
    "aventura": "card-aventura.svg",
    "cultura": "card-cultura.svg",
    "museus": "card-museus.svg",
    "natureza": "card-natureza.svg",
}

LUGARES = [
    # ---------------- praia ----------------
    ("Praia do Espelho", "praia", "Trancoso", "BA", 4.9, 2341, 2, -16.8853, -39.1108,
     "Falésias coloridas, piscinas naturais na maré baixa e um dos pores do sol mais bonitos da Bahia.",
     "Setembro a março"),
    ("Praia de Jericoacoara", "praia", "Jijoca de Jericoacoara", "CE", 4.8, 3980, 2, -2.7963, -40.5137,
     "Dunas, lagoas de água doce e vento constante — paraíso para kitesurf e para ver o sol se pôr na Duna do Pôr do Sol.",
     "Julho a dezembro"),
    ("Baía do Sancho", "praia", "Fernando de Noronha", "PE", 5.0, 6120, 4, -3.8547, -32.4419,
     "Eleita várias vezes a praia mais bonita do mundo, com mergulho em águas transparentes e vida marinha abundante.",
     "Agosto a novembro"),
    ("Praia do Rosa", "praia", "Imbituba", "SC", 4.7, 1870, 2, -28.1281, -48.6390,
     "Enseada cercada de morros verdes, ótima para surfe e para observar baleias-francas no inverno.",
     "Junho a novembro"),
    # ---------------- gastronomia ----------------
    ("Restaurante Mocotó", "gastronomia", "São Paulo", "SP", 4.8, 5102, 2, -23.4780, -46.6070,
     "Cozinha sertaneja premiada na Vila Medeiros: dadinho de tapioca, carne de sol e uma carta de cachaças imperdível.",
     "O ano todo"),
    ("A Casa do Porco", "gastronomia", "São Paulo", "SP", 4.9, 8450, 3, -23.5450, -46.6390,
     "Um dos melhores restaurantes do mundo, com menu-degustação criativo baseado em porco caipira.",
     "O ano todo"),
    ("Oteque", "gastronomia", "Rio de Janeiro", "RJ", 4.9, 2210, 4, -22.9520, -43.1970,
     "Alta gastronomia com frutos do mar do litoral fluminense em um menu degustação intimista em Botafogo.",
     "O ano todo"),
    ("Mercado Municipal de São Paulo", "gastronomia", "São Paulo", "SP", 4.6, 12000, 1, -23.5417, -46.6295,
     "O templo do sanduíche de mortadela e do pastel de bacalhau, com bancas de frutas do mundo inteiro.",
     "O ano todo"),
    # ---------------- aventura ----------------
    ("Cânion Itaimbezinho", "aventura", "Cambará do Sul", "RS", 4.8, 2410, 2, -29.1300, -50.0800,
     "Paredões de 700 metros nos Aparados da Serra, com trilhas guiadas e cachoeiras que caem no vazio.",
     "Abril a setembro"),
    ("Flutuação no Rio da Prata", "aventura", "Bonito", "MS", 4.9, 3320, 3, -21.1261, -56.4886,
     "Flutuação em água cristalina entre cardumes, com trilha na mata ciliar antes do mergulho.",
     "Maio a setembro"),
    ("Trilha da Pedra Bonita", "aventura", "Rio de Janeiro", "RJ", 4.7, 1540, 1, -22.9850, -43.2830,
     "Caminhada curta com vista aberta para São Conrado, a Pedra da Gávea e a rampa de voo livre.",
     "O ano todo"),
    # ---------------- cultura ----------------
    ("Pelourinho", "cultura", "Salvador", "BA", 4.6, 8900, 1, -12.9714, -38.5100,
     "Centro histórico tombado pela Unesco, com igrejas barrocas, ensaios de blocos afro e casarões coloridos.",
     "Dezembro a março"),
    ("Centro Histórico de Ouro Preto", "cultura", "Ouro Preto", "MG", 4.8, 5400, 2, -20.3855, -43.5035,
     "Ladeiras de pedra, igrejas de Aleijadinho e o melhor do barroco mineiro em cada esquina.",
     "Abril a outubro"),
    ("Teatro Amazonas", "cultura", "Manaus", "AM", 4.8, 6700, 1, -3.1301, -60.0234,
     "Ópera em plena floresta: cúpula de azulejos, mármore italiano e visitas guiadas diárias.",
     "Junho a novembro"),
    # ---------------- museus ----------------
    ("MASP", "museus", "São Paulo", "SP", 4.7, 9800, 1, -23.5614, -46.6559,
     "Cavaletes de vidro de Lina Bo Bardi e o maior acervo de arte europeia do hemisfério sul.",
     "O ano todo"),
    ("Instituto Inhotim", "museus", "Brumadinho", "MG", 4.9, 7300, 2, -20.1230, -44.2110,
     "Museu a céu aberto que mistura arte contemporânea e jardim botânico em 140 hectares.",
     "Abril a outubro"),
    ("Museu do Amanhã", "museus", "Rio de Janeiro", "RJ", 4.7, 11200, 1, -22.8940, -43.1795,
     "Ciência e sustentabilidade em experiências interativas, no edifício de Calatrava na Praça Mauá.",
     "O ano todo"),
    # ---------------- natureza ----------------
    ("Chapada dos Veadeiros", "natureza", "Alto Paraíso de Goiás", "GO", 4.9, 4100, 2, -14.1330, -47.5150,
     "Cerrado de altitude com cachoeiras, cânions e céu limpo para observar estrelas.",
     "Maio a outubro"),
    ("Lençóis Maranhenses", "natureza", "Barreirinhas", "MA", 5.0, 3600, 3, -2.4860, -43.0200,
     "Dunas brancas intercaladas por lagoas de água doce que se formam após as chuvas.",
     "Junho a setembro"),
    ("Cataratas do Iguaçu", "natureza", "Foz do Iguaçu", "PR", 4.9, 12000, 2, -25.6953, -54.4367,
     "275 quedas d'água entre Brasil e Argentina, com passarelas até a Garganta do Diabo.",
     "Março a junho"),
]


# Referências para a busca de fotografias reais (backend/services/fotos_lugar_service.py).
# "wikipedia": título do artigo por idioma; "palavras": termos que precisam aparecer no
# nome do arquivo das fotos georreferenciadas; "raio_km": tolerância da conferência de
# coordenadas (maior para parques extensos).
REFERENCIAS_FOTOS = {
    "Praia do Espelho": {"wikipedia": {"pt": "Praia do Espelho"}, "palavras": ["espelho"], "raio_km": 5},
    "Praia de Jericoacoara": {"wikipedia": {"pt": "Jericoacoara", "en": "Jericoacoara"},
                              "palavras": ["jericoacoara", "jeri"], "raio_km": 12},
    "Baía do Sancho": {"wikipedia": {"pt": "Baía do Sancho", "en": "Baía do Sancho"},
                       "palavras": ["sancho"], "raio_km": 5},
    "Praia do Rosa": {"wikipedia": {"pt": "Praia do Rosa"}, "palavras": ["praia do rosa"], "raio_km": 6},
    "Restaurante Mocotó": {"palavras": ["mocoto"], "raio_km": 2},
    "A Casa do Porco": {"wikipedia": {"pt": "A Casa do Porco"}, "palavras": ["casa do porco"], "raio_km": 2},
    "Oteque": {"palavras": ["oteque"], "raio_km": 2},
    "Mercado Municipal de São Paulo": {"wikipedia": {"pt": "Mercado Municipal de São Paulo"},
                                       "palavras": ["mercado municipal", "mercadao"], "raio_km": 2},
    "Cânion Itaimbezinho": {"wikipedia": {"pt": "Cânion Itaimbezinho"}, "palavras": ["itaimbezinho"], "raio_km": 10},
    "Flutuação no Rio da Prata": {"palavras": ["rio da prata", "recanto ecologico"], "raio_km": 8},
    "Trilha da Pedra Bonita": {"wikipedia": {"pt": "Pedra Bonita (Rio de Janeiro)"},
                               "palavras": ["pedra bonita"], "raio_km": 3},
    "Pelourinho": {"wikipedia": {"pt": "Pelourinho (Salvador)", "en": "Pelourinho"},
                   "palavras": ["pelourinho"], "raio_km": 2},
    "Centro Histórico de Ouro Preto": {"wikipedia": {"pt": "Ouro Preto", "en": "Ouro Preto"},
                                       "palavras": ["ouro preto"], "raio_km": 4},
    "Teatro Amazonas": {"wikipedia": {"pt": "Teatro Amazonas", "en": "Teatro Amazonas"},
                        "palavras": ["teatro amazonas", "amazonas theatre"], "raio_km": 2},
    "MASP": {"wikipedia": {"pt": "Museu de Arte de São Paulo", "en": "São Paulo Museum of Art"},
             "palavras": ["masp", "museu de arte de sao paulo"], "raio_km": 1.5},
    "Instituto Inhotim": {"wikipedia": {"pt": "Instituto Inhotim", "en": "Inhotim"},
                          "palavras": ["inhotim"], "raio_km": 4},
    "Museu do Amanhã": {"wikipedia": {"pt": "Museu do Amanhã", "en": "Museum of Tomorrow"},
                        "palavras": ["museu do amanha", "museum of tomorrow"], "raio_km": 1.5},
    "Chapada dos Veadeiros": {"wikipedia": {"pt": "Parque Nacional da Chapada dos Veadeiros",
                                            "en": "Chapada dos Veadeiros National Park"},
                              "palavras": ["veadeiros", "alto paraiso"], "raio_km": 40},
    "Lençóis Maranhenses": {"wikipedia": {"pt": "Parque Nacional dos Lençóis Maranhenses",
                                          "en": "Lençóis Maranhenses National Park"},
                            "palavras": ["lencois", "maranhenses"], "raio_km": 60},
    "Cataratas do Iguaçu": {"wikipedia": {"pt": "Cataratas do Iguaçu", "en": "Iguazu Falls"},
                            "palavras": ["iguacu", "iguazu", "garganta do diabo"], "raio_km": 8},
}

# Lugares cujas paisagens são candidatas ao fundo da tela inicial, em ordem de preferência.
LUGARES_FUNDO_INICIAL = [
    "Lençóis Maranhenses", "Baía do Sancho", "Cataratas do Iguaçu", "Praia de Jericoacoara",
    "Chapada dos Veadeiros", "Praia do Espelho",
]


def popular_banco():
    """Insere os dados iniciais apenas se o banco estiver vazio."""
    criados = {"interesses": 0, "lugares": 0}

    if Interesse.contar() == 0:
        for dados in INTERESSES:
            Interesse(**dados).salvar()
        criados["interesses"] = len(INTERESSES)

    if Lugar.contar() == 0:
        for (nome, categoria, cidade, estado, nota, avaliacoes, preco, lat, lon,
             descricao, epoca) in LUGARES:
            db.session.add(
                Lugar(
                    nome=nome,
                    categoria=categoria,
                    cidade=cidade,
                    estado=estado,
                    nota=nota,
                    avaliacoes=avaliacoes,
                    faixa_preco=preco,
                    latitude=lat,
                    longitude=lon,
                    descricao=descricao,
                    melhor_epoca=epoca,
                    imagem=IMAGENS.get(categoria, "card-praia.svg"),
                )
            )
        db.session.commit()
        criados["lugares"] = len(LUGARES)

    return criados
