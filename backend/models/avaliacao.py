"""Entidades Avaliacao e FotoAvaliacao (comunidade de viajantes)."""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.arquivos import url_assinada
from backend.utils.datas import agora_utc


class Avaliacao(db.Model, ModeloBase):
    __tablename__ = "avaliacoes"
    # Uma avaliação por pessoa e lugar: impede duplicidade e inflar a média.
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "lugar_id", name="uq_avaliacao_usuario_lugar"),
        db.CheckConstraint("nota >= 1 AND nota <= 5", name="ck_avaliacao_nota"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="CASCADE"), nullable=False, index=True)
    nota = db.Column(db.Integer, nullable=False)
    titulo = db.Column(db.String(120), nullable=True)
    comentario = db.Column(db.Text, nullable=False)
    data_visita = db.Column(db.Date, nullable=True)
    # Verificada = o autor tem, no Viajaí, uma viagem concluída que passou por este lugar.
    experiencia_verificada = db.Column(db.Boolean, nullable=False, default=False)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="SET NULL"), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    usuario = db.relationship("Usuario")
    lugar = db.relationship("Lugar")
    fotos = db.relationship("FotoAvaliacao", back_populates="avaliacao", cascade="all, delete-orphan")

    @classmethod
    def buscar(cls, usuario_id, lugar_id):
        return db.session.query(cls).filter(cls.usuario_id == usuario_id, cls.lugar_id == lugar_id).first()

    def to_dict(self, usuario_id=None, com_lugar=False):
        dados = {
            "id": self.id,
            "lugar_id": self.lugar_id,
            "nota": self.nota,
            "titulo": self.titulo,
            "comentario": self.comentario,
            "data_visita": self.data_visita.isoformat() if self.data_visita else None,
            "experiencia_verificada": self.experiencia_verificada,
            "autor": {
                "id": self.usuario_id,
                "nome": self.usuario.primeiro_nome if self.usuario else "Viajante",
                "iniciais": self.usuario.iniciais if self.usuario else "?",
            },
            "minha": usuario_id is not None and usuario_id == self.usuario_id,
            "fotos": [f.to_dict() for f in self.fotos],
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "editada": bool(self.atualizado_em and self.criado_em and
                            (self.atualizado_em - self.criado_em).total_seconds() > 60),
        }
        if com_lugar and self.lugar:
            dados["lugar"] = {"id": self.lugar.id, "nome": self.lugar.nome, "local": f"{self.lugar.cidade}, {self.lugar.estado}"}
        return dados


class FotoAvaliacao(db.Model, ModeloBase):
    __tablename__ = "fotos_avaliacao"

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacoes.id", ondelete="CASCADE"), nullable=False, index=True)
    arquivo = db.Column(db.String(60), nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    avaliacao = db.relationship("Avaliacao", back_populates="fotos")

    def to_dict(self):
        return {"id": self.id, "url": url_assinada("avaliacoes", self.arquivo)}
