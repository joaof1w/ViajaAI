"""Entidades Despesa e PlanejamentoOrcamento (controle financeiro por viagem)."""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc, formatar_data

CATEGORIAS_DESPESA = {
    "hospedagem": {"rotulo": "Hospedagem", "icone": "🏨", "cor": "#2f80ed"},
    "alimentacao": {"rotulo": "Alimentação", "icone": "🍽️", "cor": "#ff6b35"},
    "transporte": {"rotulo": "Transporte", "icone": "🚗", "cor": "#16a34a"},
    "passeios": {"rotulo": "Passeios", "icone": "🎟️", "cor": "#9b51e0"},
    "outros": {"rotulo": "Outros", "icone": "🧾", "cor": "#93a1ad"},
}


class Despesa(db.Model, ModeloBase):
    __tablename__ = "despesas"
    __table_args__ = (db.CheckConstraint("valor_centavos >= 0", name="ck_despesa_valor"),)

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao = db.Column(db.String(160), nullable=False)
    categoria = db.Column(db.String(20), nullable=False, default="outros")
    valor_centavos = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, nullable=True)
    pago_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    viagem = db.relationship("Viagem", back_populates="despesas")
    pago_por = db.relationship("Usuario", foreign_keys=[pago_por_id])
    criado_por = db.relationship("Usuario", foreign_keys=[criado_por_id])

    def to_dict(self):
        info = CATEGORIAS_DESPESA.get(self.categoria, CATEGORIAS_DESPESA["outros"])
        return {
            "id": self.id,
            "descricao": self.descricao,
            "categoria": self.categoria,
            "categoria_rotulo": info["rotulo"],
            "icone": info["icone"],
            "valor": self.valor_centavos / 100,
            "data": formatar_data(self.data),
            "pago_por": {"id": self.pago_por_id, "nome": self.pago_por.nome} if self.pago_por else None,
            "criado_por": self.criado_por.nome if self.criado_por else None,
        }


class PlanejamentoOrcamento(db.Model, ModeloBase):
    """Valor planejado por categoria (opcional, complementa o orçamento total)."""

    __tablename__ = "planejamento_orcamento"
    __table_args__ = (db.UniqueConstraint("viagem_id", "categoria", name="uq_planejamento_categoria"),)

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    categoria = db.Column(db.String(20), nullable=False)
    valor_centavos = db.Column(db.Integer, nullable=False, default=0)

    viagem = db.relationship("Viagem", back_populates="planejamento")
