"""Caso de uso: remover um lugar dos favoritos."""
from backend.models.favorito import Favorito
from backend.utils.erros import NaoEncontrado


class RemoverFavoritoService:
    def executar(self, usuario, lugar_id):
        favorito = Favorito.buscar(usuario.id, lugar_id)
        if favorito is None:
            raise NaoEncontrado("Este lugar não está nos seus salvos.")
        favorito.deletar()
        return {"mensagem": "Removido dos salvos.", "lugar_id": lugar_id}
