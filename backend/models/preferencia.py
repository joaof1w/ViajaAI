"""Entidade Preferencia (gostos, orçamento e localização do usuário)."""

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc
from backend.models.interesse import preferencia_interesses

FAIXAS_ORCAMENTO = {
    1: {"simbolo": "$", "rotulo": "Econômico", "descricao": "Até R$ 500"},
    2: {"simbolo": "$$", "rotulo": "Moderado", "descricao": "R$ 500–2.000"},
    3: {"simbolo": "$$$", "rotulo": "Confortável", "descricao": "R$ 2.000–5.000"},
    4: {"simbolo": "$$$$", "rotulo": "Premium", "descricao": "Acima de R$ 5.000"},
}


class Preferencia(db.Model, ModeloBase):
    __tablename__ = "preferencias"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False, index=True
    )
    orcamento = db.Column(db.Integer, default=2, nullable=False)
    cidade = db.Column(db.String(80), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    usuario = db.relationship("Usuario", back_populates="preferencia")
    interesses = db.relationship("Interesse", secondary=preferencia_interesses, lazy="joined")

    @classmethod
    def buscar_por_usuario(cls, usuario_id):
        return db.session.query(cls).filter(cls.usuario_id == usuario_id).first()

    def definir_interesses(self, interesses):
        self.interesses = list(interesses)
        return self

    @property
    def slugs_interesses(self):
        return [i.slug for i in self.interesses]

    def to_dict(self):
        faixa = FAIXAS_ORCAMENTO.get(self.orcamento, FAIXAS_ORCAMENTO[2])
        return {
            "orcamento": self.orcamento,
            "orcamento_simbolo": faixa["simbolo"],
            "orcamento_rotulo": faixa["rotulo"],
            "orcamento_descricao": faixa["descricao"],
            "cidade": self.cidade,
            "estado": self.estado,
            "interesses": [i.to_dict() for i in self.interesses],
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
