"""Caso de uso: consultar os detalhes de um lugar."""
from backend.models.favorito import Favorito
from backend.models.lugar import Lugar
from backend.services.calcular_match_service import CalcularMatchService
from backend.utils.erros import NaoEncontrado


class ObterLugarService:
    def __init__(self, servico_match=None):
        self.servico_match = servico_match or CalcularMatchService()

    def executar(self, lugar_id, usuario=None):
        lugar = Lugar.buscar_por_id(lugar_id)
        if lugar is None:
            raise NaoEncontrado("Lugar não encontrado.")

        preferencia = usuario.preferencia if usuario else None
        favorito = bool(usuario and Favorito.buscar(usuario.id, lugar.id))
        distancia = self.servico_match.distancia_para(lugar, preferencia)
        return lugar.to_dict(
            match=self.servico_match.executar(lugar, preferencia, distancia),
            distancia_km=distancia,
            favorito=favorito,
        )
