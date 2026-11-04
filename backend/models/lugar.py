"""Entidade Lugar (destinos, restaurantes e experiências)."""

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class Lugar(db.Model, ModeloBase):
    __tablename__ = "lugares"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    categoria = db.Column(db.String(40), nullable=False, index=True)  # slug do Interesse
    cidade = db.Column(db.String(80), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    descricao = db.Column(db.Text, nullable=False, default="")
    nota = db.Column(db.Float, default=0.0, nullable=False)
    avaliacoes = db.Column(db.Integer, default=0, nullable=False)
    faixa_preco = db.Column(db.Integer, default=2, nullable=False)  # 1 a 4
    imagem = db.Column(db.String(120), nullable=False, default="card-praia.svg")
    latitude = db.Column(db.Float, nullable=False, default=0.0)
    longitude = db.Column(db.Float, nullable=False, default=0.0)
    melhor_epoca = db.Column(db.String(80), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    favoritos = db.relationship("Favorito", back_populates="lugar", cascade="all, delete-orphan")

    @classmethod
    def listar_por_categoria(cls, categoria):
        return db.session.query(cls).filter(cls.categoria == categoria).all()

    @property
    def preco_simbolo(self):
        return "$" * max(1, min(4, self.faixa_preco))

    def to_dict(self, match=None, distancia_km=None, favorito=False):
        dados = {
            "id": self.id,
            "nome": self.nome,
            "categoria": self.categoria,
            "cidade": self.cidade,
            "estado": self.estado,
            "local": f"{self.cidade}, {self.estado}",
            "descricao": self.descricao,
            "nota": round(self.nota, 1),
            "avaliacoes": self.avaliacoes,
            "faixa_preco": self.faixa_preco,
            "preco_simbolo": self.preco_simbolo,
            "imagem": self.imagem,
            "melhor_epoca": self.melhor_epoca,
            "favorito": favorito,
        }
        if match is not None:
            dados["match"] = match
        if distancia_km is not None:
            dados["distancia_km"] = distancia_km
        return dados
