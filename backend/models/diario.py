"""Entidades RegistroDiario e FotoDiario (histórico e memórias de viagem)."""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.arquivos import url_assinada
from backend.utils.datas import agora_utc, formatar_data

VISIBILIDADES = {
    "privado": "Só eu",
    "participantes": "Participantes da viagem",
    "publico": "Comunidade Viajaí",
}


class RegistroDiario(db.Model, ModeloBase):
    __tablename__ = "registros_diario"
    __table_args__ = (db.CheckConstraint("nota_pessoal IS NULL OR (nota_pessoal >= 1 AND nota_pessoal <= 5)",
                                         name="ck_diario_nota"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="SET NULL"), nullable=True, index=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="SET NULL"), nullable=True)
    titulo = db.Column(db.String(140), nullable=False)
    relato = db.Column(db.Text, nullable=True)
    data = db.Column(db.Date, nullable=False, index=True)
    local = db.Column(db.String(160), nullable=True)
    cidade = db.Column(db.String(80), nullable=True)
    estado = db.Column(db.String(60), nullable=True)
    nota_pessoal = db.Column(db.Integer, nullable=True)
    visibilidade = db.Column(db.String(14), nullable=False, default="privado")
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    usuario = db.relationship("Usuario")
    viagem = db.relationship("Viagem")
    lugar = db.relationship("Lugar")
    fotos = db.relationship("FotoDiario", back_populates="registro", cascade="all, delete-orphan")

    def to_dict(self, usuario_id=None):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "relato": self.relato,
            "data": formatar_data(self.data),
            "local": self.local,
            "cidade": self.cidade,
            "estado": self.estado,
            "nota_pessoal": self.nota_pessoal,
            "visibilidade": self.visibilidade,
            "visibilidade_rotulo": VISIBILIDADES.get(self.visibilidade, self.visibilidade),
            "viagem": {"id": self.viagem.id, "titulo": self.viagem.titulo} if self.viagem else None,
            "lugar": {"id": self.lugar.id, "nome": self.lugar.nome} if self.lugar else None,
            "autor": {"id": self.usuario_id, "nome": self.usuario.primeiro_nome if self.usuario else ""},
            "meu": usuario_id == self.usuario_id,
            "fotos": [f.to_dict() for f in self.fotos],
        }


class FotoDiario(db.Model, ModeloBase):
    __tablename__ = "fotos_diario"

    id = db.Column(db.Integer, primary_key=True)
    registro_id = db.Column(db.Integer, db.ForeignKey("registros_diario.id", ondelete="CASCADE"), nullable=False, index=True)
    arquivo = db.Column(db.String(60), nullable=False)
    legenda = db.Column(db.String(160), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    registro = db.relationship("RegistroDiario", back_populates="fotos")

    def to_dict(self):
        return {"id": self.id, "url": url_assinada("diario", self.arquivo), "legenda": self.legenda}
