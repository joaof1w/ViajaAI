"""Entidade Favorito (lugares salvos pelo usuário)."""

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class Favorito(db.Model, ModeloBase):
    __tablename__ = "favoritos"
    __table_args__ = (db.UniqueConstraint("usuario_id", "lugar_id", name="uq_favorito_usuario_lugar"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id"), nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    usuario = db.relationship("Usuario", back_populates="favoritos")
    lugar = db.relationship("Lugar", back_populates="favoritos")

    @classmethod
    def buscar(cls, usuario_id, lugar_id):
        return (
            db.session.query(cls)
            .filter(cls.usuario_id == usuario_id, cls.lugar_id == lugar_id)
            .first()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "lugar": self.lugar.to_dict(favorito=True) if self.lugar else None,
        }
