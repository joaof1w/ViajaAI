"""Entidade Usuario."""
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc


class Usuario(db.Model, ModeloBase):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    verificado = db.Column(db.Boolean, default=False, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    preferencia = db.relationship(
        "Preferencia", back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    favoritos = db.relationship("Favorito", back_populates="usuario", cascade="all, delete-orphan")
    codigos = db.relationship(
        "CodigoVerificacao", back_populates="usuario", cascade="all, delete-orphan"
    )
    mensagens = db.relationship(
        "MensagemChat", back_populates="usuario", cascade="all, delete-orphan"
    )

    # ---------- comportamento da entidade ----------
    def definir_senha(self, senha_pura):
        self.senha_hash = generate_password_hash(senha_pura)

    def conferir_senha(self, senha_pura):
        return check_password_hash(self.senha_hash, senha_pura or "")

    def gerar_token(self):
        self.token = secrets.token_hex(24)
        return self.token

    @property
    def iniciais(self):
        partes = [p for p in self.nome.split() if p]
        if not partes:
            return "?"
        return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()

    @property
    def primeiro_nome(self):
        return self.nome.split()[0] if self.nome else ""

    @classmethod
    def buscar_por_email(cls, email):
        return db.session.query(cls).filter(cls.email == (email or "").strip().lower()).first()

    @classmethod
    def buscar_por_token(cls, token):
        if not token:
            return None
        return db.session.query(cls).filter(cls.token == token).first()

    def to_dict(self, incluir_preferencias=False):
        dados = {
            "id": self.id,
            "nome": self.nome,
            "primeiro_nome": self.primeiro_nome,
            "iniciais": self.iniciais,
            "email": self.email,
            "verificado": self.verificado,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
        if incluir_preferencias:
            dados["preferencias"] = self.preferencia.to_dict() if self.preferencia else None
        return dados
