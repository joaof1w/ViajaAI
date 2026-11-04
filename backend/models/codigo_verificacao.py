"""Entidade CodigoVerificacao (código de 6 dígitos enviado por e-mail)."""
import random
from datetime import timedelta

from backend.config import Config
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class CodigoVerificacao(db.Model, ModeloBase):
    __tablename__ = "codigos_verificacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    codigo = db.Column(db.String(6), nullable=False)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    usuario = db.relationship("Usuario", back_populates="codigos")

    @staticmethod
    def gerar_codigo():
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def emitir_para(cls, usuario):
        """Invalida códigos anteriores e cria um novo."""
        for antigo in cls.listar_por_usuario(usuario.id):
            antigo.usado = True
        codigo = cls(
            usuario_id=usuario.id,
            codigo=cls.gerar_codigo(),
            expira_em=agora_utc() + timedelta(minutes=Config.CODIGO_VALIDADE_MINUTOS),
        )
        return codigo.salvar()

    @classmethod
    def listar_por_usuario(cls, usuario_id):
        return (
            db.session.query(cls)
            .filter(cls.usuario_id == usuario_id, cls.usado.is_(False))
            .order_by(cls.criado_em.desc())
            .all()
        )

    @classmethod
    def buscar_valido(cls, usuario_id, codigo):
        return (
            db.session.query(cls)
            .filter(
                cls.usuario_id == usuario_id,
                cls.codigo == codigo,
                cls.usado.is_(False),
                cls.expira_em >= agora_utc(),
            )
            .first()
        )

    def marcar_como_usado(self):
        self.usado = True
        db.session.commit()
        return self

    @property
    def expirado(self):
        return agora_utc() > self.expira_em
