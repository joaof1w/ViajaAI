"""Entidade MigracaoAplicada: controle das migrações de banco já executadas."""
from backend.extensions import db
from backend.utils.datas import agora_utc


class MigracaoAplicada(db.Model):
    __tablename__ = "migracoes_aplicadas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False)
    aplicada_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
