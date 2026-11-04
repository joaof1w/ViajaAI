"""Entidades SugestaoViagem e VotoSugestao (decisões do grupo)."""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class SugestaoViagem(db.Model, ModeloBase):
    __tablename__ = "sugestoes_viagem"

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(db.String(10), nullable=False, default="aberta")  # aberta | aprovada | rejeitada
    decidido_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey("atividades_roteiro.id", ondelete="SET NULL"), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    decidido_em = db.Column(db.DateTime, nullable=True)

    viagem = db.relationship("Viagem", back_populates="sugestoes")
    autor = db.relationship("Usuario", foreign_keys=[autor_id])
    decidido_por = db.relationship("Usuario", foreign_keys=[decidido_por_id])
    lugar = db.relationship("Lugar")
    votos = db.relationship("VotoSugestao", back_populates="sugestao", cascade="all, delete-orphan")

    def to_dict(self, usuario_id=None):
        favor = sum(1 for v in self.votos if v.valor > 0)
        contra = sum(1 for v in self.votos if v.valor < 0)
        meu = next((v.valor for v in self.votos if v.usuario_id == usuario_id), 0)
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "lugar": {"id": self.lugar.id, "nome": self.lugar.nome} if self.lugar else None,
            "autor": {"id": self.autor_id, "nome": self.autor.nome if self.autor else ""},
            "status": self.status,
            "votos_favor": favor,
            "votos_contra": contra,
            "saldo": favor - contra,
            "meu_voto": meu,
            "decidido_por": self.decidido_por.nome if self.decidido_por else None,
            "atividade_id": self.atividade_id,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }


class VotoSugestao(db.Model, ModeloBase):
    __tablename__ = "votos_sugestao"
    __table_args__ = (db.UniqueConstraint("sugestao_id", "usuario_id", name="uq_voto_usuario"),)

    id = db.Column(db.Integer, primary_key=True)
    sugestao_id = db.Column(
        db.Integer, db.ForeignKey("sugestoes_viagem.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    valor = db.Column(db.Integer, nullable=False)  # +1 ou -1

    sugestao = db.relationship("SugestaoViagem", back_populates="votos")
