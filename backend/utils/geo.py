"""Cálculo de distância entre a cidade do usuário e os lugares."""
from math import asin, cos, radians, sin, sqrt

# Coordenadas aproximadas das cidades atendidas pelo app
CIDADES = {
    ("são paulo", "SP"): (-23.5505, -46.6333),
    ("campinas", "SP"): (-22.9099, -47.0626),
    ("santos", "SP"): (-23.9608, -46.3336),
    ("rio de janeiro", "RJ"): (-22.9068, -43.1729),
    ("belo horizonte", "MG"): (-19.9167, -43.9345),
    ("curitiba", "PR"): (-25.4284, -49.2733),
    ("florianópolis", "SC"): (-27.5954, -48.5480),
    ("porto alegre", "RS"): (-30.0346, -51.2177),
    ("salvador", "BA"): (-12.9777, -38.5016),
    ("recife", "PE"): (-8.0476, -34.8770),
    ("fortaleza", "CE"): (-3.7319, -38.5267),
    ("natal", "RN"): (-5.7945, -35.2110),
    ("brasília", "DF"): (-15.7939, -47.8828),
    ("manaus", "AM"): (-3.1190, -60.0217),
    ("belém", "PA"): (-1.4558, -48.5039),
}

PADRAO = CIDADES[("são paulo", "SP")]


def coordenadas_da_cidade(cidade, estado):
    """Retorna (lat, lon) da cidade informada; cai no padrão quando desconhecida."""
    chave = ((cidade or "").strip().lower(), (estado or "").strip().upper())
    if chave in CIDADES:
        return CIDADES[chave]
    for (nome, uf), coord in CIDADES.items():
        if uf == chave[1]:
            return coord
    return PADRAO


def distancia_km(origem, destino):
    """Distância de grande círculo (fórmula de Haversine), em quilômetros."""
    lat1, lon1 = radians(origem[0]), radians(origem[1])
    lat2, lon2 = radians(destino[0]), radians(destino[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return round(2 * 6371 * asin(sqrt(a)), 1)


def listar_cidades():
    return [
        {"cidade": nome.title(), "estado": uf, "rotulo": f"{nome.title()}, {uf}"}
        for (nome, uf) in CIDADES
    ]
