"""Integração externa: estabelecimentos e atrações reais próximos (Overpass API / OSM).

Os resultados são persistidos em PontoInteresse — servem de cache e de base para o
roteiro inteligente (o Vai só sugere lugares que existem nesse acervo ou no catálogo).
Horários de funcionamento vêm da tag `opening_hours` do OSM, quando existir.
"""
import json
from datetime import timedelta

from backend.config import Config
from backend.extensions import db
from backend.models.cache_externo import CacheExterno
from backend.models.ponto_interesse import PontoInteresse
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.datas import agora_utc
from backend.utils.erros import IntegracaoIndisponivel
from backend.utils.geo import distancia_km

# tag OSM -> tipo do Viajaí
CLASSIFICACAO = [
    ("amenity", "restaurant", "restaurante"),
    ("amenity", "cafe", "cafe"),
    ("tourism", "museum", "museu"),
    ("tourism", "gallery", "museu"),
    ("tourism", "viewpoint", "mirante"),
    ("tourism", "attraction", "atracao"),
    ("historic", None, "historico"),
    ("leisure", "park", "parque"),
    ("natural", "beach", "praia"),
    ("natural", "waterfall", "natureza"),
    ("amenity", "theatre", "cultura"),
]

TIPOS_ROTULO = {
    "restaurante": "Restaurante", "cafe": "Café", "museu": "Museu", "mirante": "Mirante",
    "atracao": "Atração", "historico": "Patrimônio histórico", "parque": "Parque",
    "praia": "Praia", "natureza": "Natureza", "cultura": "Cultura",
}

# tipo do ponto -> categoria de interesse do usuário
TIPO_PARA_INTERESSE = {
    "restaurante": "gastronomia", "cafe": "gastronomia", "museu": "museus", "mirante": "natureza",
    "atracao": "cultura", "historico": "cultura", "parque": "natureza", "praia": "praia",
    "natureza": "aventura", "cultura": "cultura",
}


def classificar(tags):
    for chave, valor, tipo in CLASSIFICACAO:
        if chave in tags and (valor is None or tags[chave] == valor):
            return tipo
    return None


class PontosInteresseService:
    RAIO_PADRAO_M = 4000

    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    def _consulta(self, latitude, longitude, raio):
        filtros = [
            'nwr["amenity"~"^(restaurant|cafe|theatre)$"]["name"]',
            'nwr["tourism"~"^(museum|gallery|viewpoint|attraction)$"]["name"]',
            'nwr["historic"]["name"]',
            'nwr["leisure"="park"]["name"]',
            'nwr["natural"~"^(beach|waterfall)$"]["name"]',
        ]
        corpo = "".join(f"{f}(around:{raio},{latitude},{longitude});" for f in filtros)
        return f"[out:json][timeout:20];({corpo});out center 150;"

    def atualizar(self, latitude, longitude, raio=None):
        """Busca no Overpass (no máximo 1x por semana por região) e grava os pontos."""
        raio = int(raio or self.RAIO_PADRAO_M)
        chave = f"overpass:{round(latitude, 2)}:{round(longitude, 2)}:{raio}"
        if CacheExterno.ler(chave) is not None:
            return {"atualizado": False, "motivo": "cache"}
        dados = self.cliente.requisitar_json(
            self.config.OVERPASS_URL, metodo="POST", dados={"data": self._consulta(latitude, longitude, raio)}
        )
        total = 0
        for elemento in dados.get("elements", []):
            tags = elemento.get("tags") or {}
            tipo = classificar(tags)
            nome = (tags.get("name") or "").strip()
            lat = elemento.get("lat") or (elemento.get("center") or {}).get("lat")
            lon = elemento.get("lon") or (elemento.get("center") or {}).get("lon")
            if not tipo or not nome or lat is None or lon is None:
                continue
            ponto = (
                db.session.query(PontoInteresse)
                .filter(PontoInteresse.osm_tipo == elemento["type"], PontoInteresse.osm_id == elemento["id"])
                .first()
            ) or PontoInteresse(osm_tipo=elemento["type"], osm_id=elemento["id"])
            ponto.nome = nome[:200]
            ponto.tipo = tipo
            ponto.latitude, ponto.longitude = float(lat), float(lon)
            rua = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
            ponto.endereco = ", ".join(filter(None, [rua, tags.get("addr:city")]))[:240] or None
            ponto.funcionamento = (tags.get("opening_hours") or "")[:200] or None
            ponto.site = (tags.get("website") or tags.get("contact:website") or "")[:300] or None
            ponto.tags = json.dumps({k: v for k, v in tags.items() if k in (
                "cuisine", "tourism", "amenity", "historic", "leisure", "natural", "wheelchair", "fee")})
            db.session.add(ponto)
            total += 1
        db.session.commit()
        CacheExterno.gravar(chave, {"total": total}, self.config.CACHE_EXTERNO_HORAS)
        return {"atualizado": True, "total": total}

    def proximos(self, latitude, longitude, raio_km=4, tipos=None, limite=60, buscar_externo=True):
        """Pontos já conhecidos perto da coordenada (atualiza pelo Overpass se possível)."""
        aviso = None
        if buscar_externo:
            try:
                self.atualizar(latitude, longitude, raio=int(raio_km * 1000))
            except IntegracaoIndisponivel as erro:
                aviso = erro.mensagem
        delta = raio_km / 111.0 * 1.3
        consulta = db.session.query(PontoInteresse).filter(
            PontoInteresse.latitude.between(latitude - delta, latitude + delta),
            PontoInteresse.longitude.between(longitude - delta * 1.4, longitude + delta * 1.4),
        )
        if tipos:
            consulta = consulta.filter(PontoInteresse.tipo.in_(tipos))
        itens = []
        for ponto in consulta.limit(800).all():
            distancia = distancia_km((latitude, longitude), (ponto.latitude, ponto.longitude))
            if distancia <= raio_km:
                itens.append((distancia, ponto))
        itens.sort(key=lambda par: par[0])
        return {"pontos": [p.to_dict(distancia_km=d) for d, p in itens[:limite]], "aviso": aviso}

    @staticmethod
    def limpar_antigos(dias=90):
        limite = agora_utc() - timedelta(days=dias)
        db.session.query(PontoInteresse).filter(PontoInteresse.atualizado_em < limite).delete()
        db.session.commit()
