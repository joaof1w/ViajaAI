"""Entidades Viagem e ParticipanteViagem (planejador e viagens em grupo)."""

from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc, formatar_data, hoje

TIPOS_VIAGEM = {
    "lazer": "Lazer",
    "aventura": "Aventura",
    "cultural": "Cultural",
    "romantica": "Romântica",
    "familia": "Em família",
    "negocios": "Negócios",
    "mochilao": "Mochilão",
}

# Papéis de quem participa (o proprietário é Viagem.proprietario_id)
PAPEIS = {
    "editor": "Editor — organiza roteiro, gastos, agenda e checklist",
    "viajante": "Viajante — visualiza, sugere e vota",
}


class Viagem(db.Model, ModeloBase):
    __tablename__ = "viagens"
    __table_args__ = (db.CheckConstraint("data_volta >= data_ida", name="ck_viagem_datas"),)

    id = db.Column(db.Integer, primary_key=True)
    proprietario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="SET NULL"), nullable=True, index=True)
    titulo = db.Column(db.String(120), nullable=False)
    destino = db.Column(db.String(160), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    data_ida = db.Column(db.Date, nullable=False)
    data_volta = db.Column(db.Date, nullable=False)
    viajantes = db.Column(db.Integer, nullable=False, default=1)
    tipo = db.Column(db.String(20), nullable=False, default="lazer")
    orcamento_centavos = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    preferencias = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)

    proprietario = db.relationship("Usuario", foreign_keys=[proprietario_id])
    lugar = db.relationship("Lugar")
    participantes = db.relationship(
        "ParticipanteViagem", back_populates="viagem", cascade="all, delete-orphan"
    )
    roteiros = db.relationship("Roteiro", back_populates="viagem", cascade="all, delete-orphan")
    despesas = db.relationship("Despesa", back_populates="viagem", cascade="all, delete-orphan")
    planejamento = db.relationship(
        "PlanejamentoOrcamento", back_populates="viagem", cascade="all, delete-orphan"
    )
    itens_checklist = db.relationship("ItemChecklist", back_populates="viagem", cascade="all, delete-orphan")
    compromissos = db.relationship("Compromisso", back_populates="viagem", cascade="all, delete-orphan")
    sugestoes = db.relationship("SugestaoViagem", back_populates="viagem", cascade="all, delete-orphan")

    # ---------- regras da entidade ----------
    @property
    def duracao_dias(self):
        return (self.data_volta - self.data_ida).days + 1

    def status_em(self, referencia=None):
        referencia = referencia or hoje()
        if self.data_volta < referencia:
            return "concluida"
        if self.data_ida <= referencia:
            return "em_andamento"
        return "futura"

    @property
    def status(self):
        return self.status_em()

    def data_do_dia(self, numero_dia):
        from datetime import timedelta

        return self.data_ida + timedelta(days=int(numero_dia) - 1)

    def participante(self, usuario_id):
        for item in self.participantes:
            if item.usuario_id == usuario_id:
                return item
        return None

    def papel_de(self, usuario_id):
        """'proprietario', 'editor', 'viajante', 'convidado' (pendente) ou None."""
        if self.proprietario_id == usuario_id:
            return "proprietario"
        item = self.participante(usuario_id)
        if item is None or item.status == "recusado":
            return None
        if item.status == "pendente":
            return "convidado"
        return item.papel

    def membros_ids(self):
        ids = {self.proprietario_id}
        ids.update(p.usuario_id for p in self.participantes if p.status == "aceito")
        return ids

    @property
    def roteiro_ativo(self):
        for roteiro in self.roteiros:
            if roteiro.ativo:
                return roteiro
        return None

    def to_dict(self, usuario_id=None, resumo=False):
        dados = {
            "id": self.id,
            "titulo": self.titulo,
            "destino": self.destino,
            "lugar_id": self.lugar_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "data_ida": formatar_data(self.data_ida),
            "data_volta": formatar_data(self.data_volta),
            "duracao_dias": self.duracao_dias,
            "viajantes": self.viajantes,
            "tipo": self.tipo,
            "tipo_rotulo": TIPOS_VIAGEM.get(self.tipo, self.tipo),
            "status": self.status,
            "orcamento": (self.orcamento_centavos or 0) / 100 if self.orcamento_centavos is not None else None,
            "proprietario": {"id": self.proprietario_id, "nome": self.proprietario.nome if self.proprietario else ""},
            "compartilhada": any(p.status == "aceito" for p in self.participantes),
            "total_participantes": 1 + sum(1 for p in self.participantes if p.status == "aceito"),
        }
        if usuario_id is not None:
            dados["meu_papel"] = self.papel_de(usuario_id)
        if self.lugar is not None:
            dados["lugar"] = {"id": self.lugar.id, "nome": self.lugar.nome, "categoria": self.lugar.categoria,
                              "imagem": self.lugar.imagem, "foto": self.lugar.foto_principal_dict()}
        if not resumo:
            dados["observacoes"] = self.observacoes
            dados["preferencias"] = self.preferencias
            dados["criado_em"] = self.criado_em.isoformat() if self.criado_em else None
        return dados


class ParticipanteViagem(db.Model, ModeloBase):
    __tablename__ = "participantes_viagem"
    __table_args__ = (db.UniqueConstraint("viagem_id", "usuario_id", name="uq_participante_viagem"),)

    id = db.Column(db.Integer, primary_key=True)
    viagem_id = db.Column(db.Integer, db.ForeignKey("viagens.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    convidado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    papel = db.Column(db.String(12), nullable=False, default="viajante")
    status = db.Column(db.String(10), nullable=False, default="pendente")  # pendente | aceito | recusado
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)
    respondido_em = db.Column(db.DateTime, nullable=True)

    viagem = db.relationship("Viagem", back_populates="participantes")
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id])
    convidado_por = db.relationship("Usuario", foreign_keys=[convidado_por_id])

    @classmethod
    def convites_pendentes(cls, usuario_id):
        return (
            db.session.query(cls)
            .filter(cls.usuario_id == usuario_id, cls.status == "pendente")
            .order_by(cls.criado_em.desc())
            .all()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "usuario": {
                "id": self.usuario_id,
                "nome": self.usuario.nome if self.usuario else "",
                "iniciais": self.usuario.iniciais if self.usuario else "?",
                "email": self.usuario.email if self.usuario else "",
            },
            "papel": self.papel,
            "status": self.status,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def to_convite_dict(self):
        viagem = self.viagem
        return {
            "id": self.id,
            "papel": self.papel,
            "convidado_por": self.convidado_por.nome if self.convidado_por else "",
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            # Só o resumo: o convidado ainda não tem acesso aos dados da viagem.
            "viagem": {
                "id": viagem.id,
                "titulo": viagem.titulo,
                "destino": viagem.destino,
                "data_ida": formatar_data(viagem.data_ida),
                "data_volta": formatar_data(viagem.data_volta),
            },
        }



