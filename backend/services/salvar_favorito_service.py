"""Caso de uso: salvar um lugar nos favoritos."""
from backend.models.favorito import Favorito
from backend.models.lugar import Lugar
from backend.utils.erros import NaoEncontrado


class SalvarFavoritoService:
    def executar(self, usuario, lugar_id):
        lugar = Lugar.buscar_por_id(lugar_id)
        if lugar is None:
            raise NaoEncontrado("Lugar não encontrado.")

        favorito = Favorito.buscar(usuario.id, lugar.id)
        if favorito is None:
            favorito = Favorito(usuario_id=usuario.id, lugar_id=lugar.id).salvar()

        return {
            "mensagem": f"{lugar.nome} foi salvo.",
            "favorito": favorito.to_dict(),
        }
