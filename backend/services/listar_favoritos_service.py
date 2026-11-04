"""Caso de uso: listar os lugares salvos pelo usuário."""
from backend.repositories.favorito_repository import FavoritoRepository
from backend.services.calcular_match_service import CalcularMatchService


class ListarFavoritosService:
    def __init__(self, repositorio=None, servico_match=None):
        self.repositorio = repositorio or FavoritoRepository()
        self.servico_match = servico_match or CalcularMatchService()

    def executar(self, usuario):
        preferencia = usuario.preferencia
        itens = []
        for favorito in self.repositorio.listar_com_lugar(usuario.id):
            lugar = favorito.lugar
            if lugar is None:
                continue
            distancia = self.servico_match.distancia_para(lugar, preferencia)
            itens.append(
                lugar.to_dict(
                    match=self.servico_match.executar(lugar, preferencia, distancia),
                    distancia_km=distancia,
                    favorito=True,
                )
            )
        return {"total": len(itens), "lugares": itens}
