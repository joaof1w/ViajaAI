"""Caso de uso: Comparador de Destinos (feature 5) — até três lugares lado a lado.

Cada critério só é preenchido com dados existentes: catálogo, avaliações reais da
comunidade, distância calculada, previsão do Open-Meteo (quando disponível) e pontos
do OpenStreetMap já conhecidos. O que não existe aparece como "sem dados".
"""
from collections import Counter

from sqlalchemy import func

from backend.extensions import db
from backend.models.avaliacao import Avaliacao
from backend.models.interesse import Interesse
from backend.models.lugar import Lugar
from backend.repositories.favorito_repository import FavoritoRepository
from backend.services.calcular_match_service import CalcularMatchService
from backend.services.integracoes.clima_service import ClimaService
from backend.services.integracoes.pontos_interesse_service import PontosInteresseService
from backend.utils.erros import ErroDeValidacao
from backend.utils.geo import distancia_km

RAIO_ATRACOES_KM = 60
MAXIMO = 3


class CompararDestinosService:
    def __init__(self, servico_match=None, servico_clima=None, servico_pontos=None):
        self.servico_match = servico_match or CalcularMatchService()
        self.servico_clima = servico_clima or ClimaService()
        self.servico_pontos = servico_pontos or PontosInteresseService()

    def executar(self, ids, usuario=None, incluir_clima=True):
        ids = list(dict.fromkeys(ids or []))
        if not 2 <= len(ids) <= MAXIMO:
            raise ErroDeValidacao(f"Escolha de 2 a {MAXIMO} destinos para comparar.", campo="ids")
        lugares = {l.id: l for l in db.session.query(Lugar).filter(Lugar.id.in_(ids)).all()}
        if len(lugares) != len(ids):
            raise ErroDeValidacao("Algum destino não foi encontrado.", campo="ids")

        preferencia = usuario.preferencia if usuario else None
        interesses = set(preferencia.slugs_interesses) if preferencia else set()
        nomes_interesses = {i.slug: i.nome for i in Interesse.listar_todos()}
        favoritos = FavoritoRepository().ids_favoritados(usuario.id) if usuario else set()
        todos = Lugar.listar_todos()
        comunidade = dict(
            (lid, (media, total)) for lid, media, total in db.session.query(
                Avaliacao.lugar_id, func.avg(Avaliacao.nota), func.count(Avaliacao.id)
            ).filter(Avaliacao.lugar_id.in_(ids)).group_by(Avaliacao.lugar_id).all()
        )

        itens = []
        for lugar_id in ids:
            lugar = lugares[lugar_id]
            distancia = self.servico_match.distancia_para(lugar, preferencia) if preferencia else None
            vizinhos = [o for o in todos if o.id != lugar.id and
                        distancia_km((lugar.latitude, lugar.longitude), (o.latitude, o.longitude)) <= RAIO_ATRACOES_KM]
            por_categoria = Counter(o.categoria for o in vizinhos)
            pontos = self.servico_pontos.proximos(lugar.latitude, lugar.longitude, raio_km=5, limite=300,
                                                  buscar_externo=False)["pontos"]
            media, total = comunidade.get(lugar.id, (None, 0))
            itens.append({
                "lugar": lugar.to_dict(favorito=lugar.id in favoritos),
                "preco": {"faixa": lugar.faixa_preco, "simbolo": lugar.preco_simbolo},
                "avaliacao": {"catalogo": round(lugar.nota, 1), "catalogo_total": lugar.avaliacoes,
                              "comunidade": round(float(media), 1) if media is not None else None,
                              "comunidade_total": int(total or 0)},
                "atracoes": {
                    "catalogo_proximos": len(vizinhos),
                    "por_categoria": dict(por_categoria),
                    "exemplos": [o.nome for o in sorted(vizinhos, key=lambda o: -o.nota)[:4]],
                    "openstreetmap": dict(Counter(p["tipo"] for p in pontos)) or None,
                },
                "caracteristicas": {"categoria": lugar.categoria,
                                    "categoria_nome": nomes_interesses.get(lugar.categoria, lugar.categoria),
                                    "tipo": lugar.tipo, "melhor_epoca": lugar.melhor_epoca,
                                    "descricao": lugar.descricao},
                "clima": self.servico_clima.executar(lugar.latitude, lugar.longitude) if incluir_clima else None,
                "localizacao": {"local": f"{lugar.cidade}, {lugar.estado}", "latitude": lugar.latitude,
                                "longitude": lugar.longitude, "distancia_km": distancia},
                "compatibilidade": {
                    "match": self.servico_match.executar(lugar, preferencia, distancia),
                    "combina_com": [nomes_interesses.get(c, c) for c in {lugar.categoria} | set(por_categoria)
                                    if c in interesses],
                },
            })
        return {"itens": itens, "destaques": self._destaques(itens), "personalizado": preferencia is not None,
                "aviso_distancias": "Distâncias em linha reta a partir da sua cidade."}

    @staticmethod
    def _destaques(itens):
        def melhor(chave, reverso=True, filtro=lambda v: v is not None):
            validos = [(chave(i), i["lugar"]["id"]) for i in itens if filtro(chave(i))]
            if len(validos) < 2:
                return None
            alvo = max(validos)[0] if reverso else min(validos)[0]
            vencedores = [lid for valor, lid in validos if valor == alvo]
            return vencedores if len(vencedores) < len(itens) else None

        return {
            "menor_preco": melhor(lambda i: i["preco"]["faixa"], reverso=False),
            "melhor_nota": melhor(lambda i: i["avaliacao"]["catalogo"]),
            "melhor_comunidade": melhor(lambda i: i["avaliacao"]["comunidade"]),
            "mais_atracoes": melhor(lambda i: i["atracoes"]["catalogo_proximos"]),
            "mais_perto": melhor(lambda i: i["localizacao"]["distancia_km"], reverso=False),
            "maior_match": melhor(lambda i: i["compatibilidade"]["match"]),
        }
