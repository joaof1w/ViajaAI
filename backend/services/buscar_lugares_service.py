"""Caso de uso: buscar lugares por texto, categoria, orçamento e estado."""
from backend.repositories.favorito_repository import FavoritoRepository
from backend.repositories.lugar_repository import LugarRepository
from backend.services.calcular_match_service import CalcularMatchService


class BuscarLugaresService:
    ORDENACOES_VALIDAS = ("nota", "populares", "preco", "nome", "match")

    def __init__(self, repositorio=None, repositorio_favoritos=None, servico_match=None):
        self.repositorio = repositorio or LugarRepository()
        self.repositorio_favoritos = repositorio_favoritos or FavoritoRepository()
        self.servico_match = servico_match or CalcularMatchService()

    def executar(self, usuario=None, filtros=None):
        filtros = filtros or {}
        ordenar = filtros.get("ordenar") or "nota"
        if ordenar not in self.ORDENACOES_VALIDAS:
            ordenar = "nota"

        lugares = self.repositorio.buscar_com_filtros(
            categoria=filtros.get("categoria"),
            texto=filtros.get("texto"),
            faixa_preco_maxima=filtros.get("preco_maximo"),
            estado=filtros.get("estado"),
            nota_minima=filtros.get("nota_minima"),
            ordenar_por="nota" if ordenar == "match" else ordenar,
            limite=filtros.get("limite", 60),
        )

        preferencia = usuario.preferencia if usuario else None
        salvos = self.repositorio_favoritos.ids_favoritados(usuario.id) if usuario else set()

        itens = []
        for lugar in lugares:
            distancia = self.servico_match.distancia_para(lugar, preferencia)
            itens.append(
                lugar.to_dict(
                    match=self.servico_match.executar(lugar, preferencia, distancia),
                    distancia_km=distancia,
                    favorito=lugar.id in salvos,
                )
            )

        if ordenar == "match":
            itens.sort(key=lambda item: item["match"], reverse=True)

        return {"total": len(itens), "filtros": filtros, "lugares": itens}
