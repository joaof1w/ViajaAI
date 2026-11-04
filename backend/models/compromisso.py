"""Entidade Compromisso (agenda/calendário da viagem: reservas, passeios, transportes)."""
from datetime import timedelta

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc

TIPOS_COMPROMISSO = {
    "passeio": {"rotulo": "Passeio", "icone": "🎟️"},
    "reserva": {"rotulo": "Reserva", "icone": "📌"},
    "transporte": {"rotulo": "Transporte", "icone": "✈️"},
    "hospedagem": {"rotulo": "Hospedagem", "icone": "🏨"},
    "refeicao": {"rotulo": "Refeição", "icone": "🍽️"},
    "outro": {"rotulo": "Outro", "icone": "🗓️"},
}


class Compromisso(db.Model, ModeloBase):
    __tablename__ = "compromissos"

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo = db.Column(db.String(160), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="outro")
    inicio = db.Column(db.DateTime, nullable=False, index=True)
    duracao_min = db.Column(db.Integer, nullable=False, default=60)
    local = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    viagem = db.relationship("Viagem", back_populates="compromissos")

    @property
    def fim(self):
        return self.inicio + timedelta(minutes=self.duracao_min or 0)

    def to_dict(self):
        info = TIPOS_COMPROMISSO.get(self.tipo, TIPOS_COMPROMISSO["outro"])
        return {
            "id": self.id,
            "titulo": self.titulo,
            "tipo": self.tipo,
            "tipo_rotulo": info["rotulo"],
            "icone": info["icone"],
            "inicio": self.inicio.isoformat(timespec="minutes"),
            "fim": self.fim.isoformat(timespec="minutes"),
            "duracao_min": self.duracao_min,
            "local": self.local,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "observacoes": self.observacoes,
        }
