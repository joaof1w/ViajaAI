"""Caso de uso: listar todos os lugares (com match, distância e marcação de favorito)."""
from backend.repositories.favorito_repository import FavoritoRepository
from backend.repositories.lugar_repository import LugarRepository
from backend.services.calcular_match_service import CalcularMatchService


class ListarLugaresService:
    def __init__(self, repositorio=None, repositorio_favoritos=None, servico_match=None):
        self.repositorio = repositorio or LugarRepository()
        self.repositorio_favoritos = repositorio_favoritos or FavoritoRepository()
        self.servico_match = servico_match or CalcularMatchService()

    def executar(self, usuario=None, categoria=None, limite=60):
        lugares = self.repositorio.buscar_com_filtros(categoria=categoria, limite=limite)
        preferencia = usuario.preferencia if usuario else None
        salvos = self.repositorio_favoritos.ids_favoritados(usuario.id) if usuario else set()

        resultado = []
        for lugar in lugares:
            distancia = self.servico_match.distancia_para(lugar, preferencia)
            resultado.append(
                lugar.to_dict(
                    match=self.servico_match.executar(lugar, preferencia, distancia),
                    distancia_km=distancia,
                    favorito=lugar.id in salvos,
                )
            )
        return {"total": len(resultado), "lugares": resultado}
