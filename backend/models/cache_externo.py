"""Cache persistente das respostas de integrações externas (geocodificação, clima, POIs)."""
import json
from datetime import timedelta

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class CacheExterno(db.Model, ModeloBase):
    __tablename__ = "cache_externo"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(255), unique=True, nullable=False, index=True)
    conteudo = db.Column(db.Text, nullable=False)
    expira_em = db.Column(db.DateTime, nullable=False)

    @classmethod
    def ler(cls, chave):
        registro = db.session.query(cls).filter(cls.chave == chave).first()
        if registro is None or registro.expira_em < agora_utc():
            return None
        try:
            return json.loads(registro.conteudo)
        except ValueError:
            return None

    @classmethod
    def gravar(cls, chave, valor, horas):
        registro = db.session.query(cls).filter(cls.chave == chave).first() or cls(chave=chave)
        registro.conteudo = json.dumps(valor, ensure_ascii=False)
        registro.expira_em = agora_utc() + timedelta(hours=horas)
        registro.salvar()
        return valor
