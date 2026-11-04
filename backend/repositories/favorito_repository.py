"""Consultas especiais de Favorito (join com Lugar e checagens em lote)."""
from sqlalchemy import text
from sqlalchemy.orm import joinedload

from backend.extensions import db
from backend.models.favorito import Favorito


class FavoritoRepository:
    def __init__(self, sessao=None):
        self.sessao = sessao or db.session

    def listar_com_lugar(self, usuario_id):
        """Favoritos já com o Lugar carregado (evita N+1)."""
        return (
            self.sessao.query(Favorito)
            .options(joinedload(Favorito.lugar))
            .filter(Favorito.usuario_id == usuario_id)
            .order_by(Favorito.criado_em.desc())
            .all()
        )

    def ids_favoritados(self, usuario_id):
        """Conjunto de ids de lugares salvos — usado para marcar os cartões na listagem."""
        sql = "SELECT lugar_id FROM favoritos WHERE usuario_id = :usuario"
        linhas = self.sessao.execute(text(sql), {"usuario": usuario_id}).mappings().all()
        return {linha["lugar_id"] for linha in linhas}

    def contar_por_usuario(self, usuario_id):
        return self.sessao.query(Favorito).filter(Favorito.usuario_id == usuario_id).count()
