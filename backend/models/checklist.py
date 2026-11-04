"""Entidade ItemChecklist (o que levar e o que providenciar para a viagem)."""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc

CATEGORIAS_CHECKLIST = {
    "documentos": {"rotulo": "Documentos", "icone": "🪪"},
    "roupas": {"rotulo": "Roupas", "icone": "👕"},
    "eletronicos": {"rotulo": "Eletrônicos", "icone": "🔌"},
    "higiene": {"rotulo": "Higiene", "icone": "🧴"},
    "saude": {"rotulo": "Saúde", "icone": "💊"},
    "outros": {"rotulo": "Outros", "icone": "🎒"},
}


class ItemChecklist(db.Model, ModeloBase):
    __tablename__ = "itens_checklist"

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria = db.Column(db.String(20), nullable=False, default="outros")
    texto = db.Column(db.String(160), nullable=False)
    concluido = db.Column(db.Boolean, nullable=False, default=False)
    sugerido = db.Column(db.Boolean, nullable=False, default=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    viagem = db.relationship("Viagem", back_populates="itens_checklist")

    def to_dict(self):
        info = CATEGORIAS_CHECKLIST.get(self.categoria, CATEGORIAS_CHECKLIST["outros"])
        return {
            "id": self.id,
            "categoria": self.categoria,
            "categoria_rotulo": info["rotulo"],
            "texto": self.texto,
            "concluido": self.concluido,
            "sugerido": self.sugerido,
            "ordem": self.ordem,
        }
