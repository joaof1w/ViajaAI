"""Caso de uso: consultar o perfil do usuário logado."""
from backend.repositories.favorito_repository import FavoritoRepository


class ObterPerfilService:
    def __init__(self, repositorio_favoritos=None):
        self.repositorio_favoritos = repositorio_favoritos or FavoritoRepository()

    def executar(self, usuario):
        dados = usuario.to_dict(incluir_preferencias=True)
        dados["total_salvos"] = self.repositorio_favoritos.contar_por_usuario(usuario.id)
        dados["possui_preferencias"] = usuario.preferencia is not None
        return dados
