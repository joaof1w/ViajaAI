"""Entidade MensagemChat (histórico da conversa com o assistente Vai)."""

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class MensagemChat(db.Model, ModeloBase):
    __tablename__ = "mensagens_chat"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    autor = db.Column(db.String(10), nullable=False)  # "usuario" ou "ia"
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    usuario = db.relationship("Usuario", back_populates="mensagens")

    @classmethod
    def listar_por_usuario(cls, usuario_id, limite=50):
        return (
            db.session.query(cls)
            .filter(cls.usuario_id == usuario_id)
            .order_by(cls.criado_em.asc(), cls.id.asc())
            .limit(limite)
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "autor": self.autor,
            "texto": self.texto,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
