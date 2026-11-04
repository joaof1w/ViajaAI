"""Entidades Roteiro (versões) e AtividadeRoteiro (atividades organizadas por dia)."""
import json

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc

CATEGORIAS_ATIVIDADE = {
    "atracao": "Atração",
    "restaurante": "Restaurante",
    "experiencia": "Experiência",
    "natureza": "Natureza",
    "cultura": "Cultura",
    "compras": "Compras",
    "transporte": "Deslocamento",
    "descanso": "Tempo livre",
    "outro": "Outro",
}


class Roteiro(db.Model, ModeloBase):
    __tablename__ = "roteiros"
    __table_args__ = (db.UniqueConstraint("viagem_id", "versao", name="uq_roteiro_versao"),)

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    versao = db.Column(db.Integer, nullable=False, default=1)
    titulo = db.Column(db.String(120), nullable=False)
    origem = db.Column(db.String(12), nullable=False, default="manual")  # manual | local | gemini | copia
    ativo = db.Column(db.Boolean, nullable=False, default=False)
    parametros = db.Column(db.Text, nullable=True)  # JSON com interesses, ritmo, orçamento...
    observacoes_ia = db.Column(db.Text, nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    viagem = db.relationship("Viagem", back_populates="roteiros")
    criado_por = db.relationship("Usuario")
    atividades = db.relationship(
        "AtividadeRoteiro",
        back_populates="roteiro",
        cascade="all, delete-orphan",
        order_by="(AtividadeRoteiro.dia, AtividadeRoteiro.ordem, AtividadeRoteiro.id)",
    )

    @classmethod
    def proxima_versao(cls, viagem_id):
        atual = db.session.query(db.func.max(cls.versao)).filter(cls.viagem_id == viagem_id).scalar()
        return (atual or 0) + 1

    def to_dict(self, com_atividades=True):
        try:
            parametros = json.loads(self.parametros) if self.parametros else {}
        except ValueError:
            parametros = {}
        dados = {
            "id": self.id,
            "viagem_id": self.viagem_id,
            "versao": self.versao,
            "titulo": self.titulo,
            "origem": self.origem,
            "ativo": self.ativo,
            "parametros": parametros,
            "observacoes_ia": self.observacoes_ia,
            "criado_por": self.criado_por.nome if self.criado_por else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "total_atividades": len(self.atividades),
        }
        if com_atividades:
            dados["atividades"] = [a.to_dict() for a in self.atividades]
        return dados


class AtividadeRoteiro(db.Model, ModeloBase):
    __tablename__ = "atividades_roteiro"

    id = db.Column(db.Integer, primary_key=True)
    roteiro_id = db.Column(db.Integer, db.ForeignKey("roteiros.id", ondelete="CASCADE"), nullable=False, index=True)
    dia = db.Column(db.Integer, nullable=False, default=1)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(20), nullable=False, default="atracao")
    horario = db.Column(db.String(5), nullable=True)  # HH:MM
    horario_sugerido = db.Column(db.Boolean, nullable=False, default=False)
    duracao_min = db.Column(db.Integer, nullable=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="SET NULL"), nullable=True)
    ponto_id = db.Column(db.Integer, db.ForeignKey("pontos_interesse.id", ondelete="SET NULL"), nullable=True)
    endereco = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    funcionamento = db.Column(db.String(200), nullable=True)  # só de fonte confiável (ex.: OSM)
    fonte = db.Column(db.String(30), nullable=True)  # catalogo | openstreetmap | manual | sugestao
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    roteiro = db.relationship("Roteiro", back_populates="atividades")
    lugar = db.relationship("Lugar")
    ponto = db.relationship("PontoInteresse")

    def to_dict(self):
        return {
            "id": self.id,
            "roteiro_id": self.roteiro_id,
            "dia": self.dia,
            "ordem": self.ordem,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "categoria": self.categoria,
            "categoria_rotulo": CATEGORIAS_ATIVIDADE.get(self.categoria, self.categoria),
            "horario": self.horario,
            "horario_sugerido": self.horario_sugerido,
            "duracao_min": self.duracao_min,
            "lugar_id": self.lugar_id,
            "ponto_id": self.ponto_id,
            "endereco": self.endereco,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "funcionamento": self.funcionamento,
            "fonte": self.fonte,
        }
