"""Entidade PermissaoAssistente: o que o Vai pode consultar (consentimento do usuário).

Todas as permissões começam desligadas — o Vai só usa viagens, finanças, agenda,
favoritos ou diário depois que o usuário autoriza no chat.
"""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc

ESCOPOS_ASSISTENTE = {
    "usar_favoritos": "Destinos favoritos",
    "usar_viagens": "Viagens planejadas, roteiros e agenda",
    "usar_financas": "Orçamentos e gastos",
    "usar_diario": "Experiências registradas no diário",
}


class PermissaoAssistente(db.Model, ModeloBase):
    __tablename__ = "permissoes_assistente"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), unique=True, nullable=False, index=True)
    usar_favoritos = db.Column(db.Boolean, nullable=False, default=False)
    usar_viagens = db.Column(db.Boolean, nullable=False, default=False)
    usar_financas = db.Column(db.Boolean, nullable=False, default=False)
    usar_diario = db.Column(db.Boolean, nullable=False, default=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    @classmethod
    def do_usuario(cls, usuario_id):
        return db.session.query(cls).filter(cls.usuario_id == usuario_id).first() or cls(usuario_id=usuario_id)

    def to_dict(self):
        return {
            "escopos": [
                {"chave": chave, "rotulo": rotulo, "ativo": bool(getattr(self, chave))}
                for chave, rotulo in ESCOPOS_ASSISTENTE.items()
            ]
        }
