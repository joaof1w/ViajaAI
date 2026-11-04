"""Entidade PontoInteresse: estabelecimentos e atrações reais vindos do OpenStreetMap.

Funciona como cache persistente do Overpass API (respeita o limite de uso do serviço)
e permite referenciar esses pontos nas atividades do roteiro.
"""
import json

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class PontoInteresse(db.Model, ModeloBase):
    __tablename__ = "pontos_interesse"
    __table_args__ = (db.UniqueConstraint("osm_tipo", "osm_id", name="uq_ponto_osm"),)

    id = db.Column(db.Integer, primary_key=True)
    osm_tipo = db.Column(db.String(10), nullable=False)  # node | way | relation
    osm_id = db.Column(db.BigInteger, nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(30), nullable=False, index=True)  # restaurante, museu, atracao...
    latitude = db.Column(db.Float, nullable=False, index=True)
    longitude = db.Column(db.Float, nullable=False, index=True)
    endereco = db.Column(db.String(240), nullable=True)
    funcionamento = db.Column(db.String(200), nullable=True)
    site = db.Column(db.String(300), nullable=True)
    tags = db.Column(db.Text, nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc, nullable=False)

    def to_dict(self, distancia_km=None):
        dados = {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "endereco": self.endereco,
            "funcionamento": self.funcionamento,
            "site": self.site,
            "fonte": "OpenStreetMap",
            "osm_url": f"https://www.openstreetmap.org/{self.osm_tipo}/{self.osm_id}",
        }
        if distancia_km is not None:
            dados["distancia_km"] = distancia_km
        return dados

    @property
    def tags_dict(self):
        try:
            return json.loads(self.tags or "{}")
        except ValueError:
            return {}
