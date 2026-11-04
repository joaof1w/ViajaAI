"""Caso de uso: gerar recomendações personalizadas para o usuário."""
from backend.repositories.favorito_repository import FavoritoRepository
from backend.repositories.lugar_repository import LugarRepository
from backend.services.calcular_match_service import CalcularMatchService
from backend.utils.erros import ErroDeNegocio


class RecomendarLugaresService:
    def __init__(self, repositorio=None, repositorio_favoritos=None, servico_match=None):
        self.repositorio = repositorio or LugarRepository()
        self.repositorio_favoritos = repositorio_favoritos or FavoritoRepository()
        self.servico_match = servico_match or CalcularMatchService()

    def executar(self, usuario, limite=8, categoria=None):
        preferencia = usuario.preferencia
        if preferencia is None:
            raise ErroDeNegocio(
                "Escolha seus interesses para receber recomendações.", campo="interesses"
            )

        categorias = preferencia.slugs_interesses
        if categoria and categoria != "todos":
            categorias = [categoria]

        candidatos = self.repositorio.buscar_candidatos_para_recomendacao(
            categorias=categorias, faixa_preco_maxima=preferencia.orcamento
        )
        if not candidatos:  # nenhum lugar nas categorias: recomenda o acervo inteiro
            candidatos = self.repositorio.buscar_candidatos_para_recomendacao(categorias=None)

        salvos = self.repositorio_favoritos.ids_favoritados(usuario.id)

        pontuados = []
        for lugar in candidatos:
            distancia = self.servico_match.distancia_para(lugar, preferencia)
            match = self.servico_match.executar(lugar, preferencia, distancia)
            pontuados.append(
                lugar.to_dict(match=match, distancia_km=distancia, favorito=lugar.id in salvos)
            )

        pontuados.sort(key=lambda item: (item["match"], item["nota"]), reverse=True)
        recomendados = pontuados[:limite]

        return {
            "perfil": {
                "interesses": preferencia.slugs_interesses,
                "orcamento": preferencia.orcamento,
                "cidade": preferencia.cidade,
                "estado": preferencia.estado,
            },
            "total": len(recomendados),
            "lugares": recomendados,
        }
