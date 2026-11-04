"""Entidade FotoLugar: fotografias reais vinculadas a cada lugar, com atribuição.

Só fotos com `verificada=True` aparecem para os usuários. A verificação é feita na
sincronização (imagem principal do artigo da Wikipédia cujas coordenadas batem com
as do lugar, ou foto georreferenciada do Wikimedia Commons perto do lugar e com o
nome dele no título) ou manualmente pela curadoria (fotos vindas de buscas no
Pexels/Unsplash entram sempre como candidatas não verificadas).
"""
from backend.extensions import db
from backend.models.base import ModeloBase
from backend.utils.datas import agora_utc

FONTES_FOTO = {
    "wikimedia": {"nome": "Wikimedia Commons", "url": "https://commons.wikimedia.org"},
    "pexels": {"nome": "Pexels", "url": "https://www.pexels.com"},
    "unsplash": {"nome": "Unsplash", "url": "https://unsplash.com"},
    "local": {"nome": "Acervo Viajaí", "url": None},
}


class FotoLugar(db.Model, ModeloBase):
    __tablename__ = "fotos_lugar"
    __table_args__ = (db.UniqueConstraint("lugar_id", "url", name="uq_foto_lugar_url"),)

    id = db.Column(db.Integer, primary_key=True)
    lugar_id = db.Column(db.Integer, db.ForeignKey("lugares.id", ondelete="CASCADE"), nullable=False, index=True)
    fonte = db.Column(db.String(20), nullable=False)
    id_externo = db.Column(db.String(200), nullable=True)
    url = db.Column(db.String(600), nullable=False)
    url_media = db.Column(db.String(600), nullable=True)
    url_miniatura = db.Column(db.String(600), nullable=True)
    largura = db.Column(db.Integer, nullable=True)
    altura = db.Column(db.Integer, nullable=True)
    titulo = db.Column(db.String(300), nullable=True)
    autor = db.Column(db.String(200), nullable=True)
    autor_url = db.Column(db.String(400), nullable=True)
    licenca = db.Column(db.String(80), nullable=True)
    licenca_url = db.Column(db.String(400), nullable=True)
    pagina_origem = db.Column(db.String(600), nullable=True)
    criterio_verificacao = db.Column(db.String(200), nullable=True)
    verificada = db.Column(db.Boolean, nullable=False, default=False, index=True)
    principal = db.Column(db.Boolean, nullable=False, default=False)
    ordem = db.Column(db.Integer, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, default=agora_utc, nullable=False)

    lugar = db.relationship("Lugar", back_populates="fotos")

    def to_dict(self, completo=False):
        fonte = FONTES_FOTO.get(self.fonte, {"nome": self.fonte, "url": None})
        dados = {
            "id": self.id,
            "url": self.url,
            "media": self.url_media or self.url,
            "miniatura": self.url_miniatura or self.url_media or self.url,
            "largura": self.largura,
            "altura": self.altura,
            "titulo": self.titulo,
            "autor": self.autor,
            "autor_url": self.autor_url,
            "licenca": self.licenca,
            "licenca_url": self.licenca_url,
            "fonte": self.fonte,
            "fonte_nome": fonte["nome"],
            "pagina_origem": self.pagina_origem or fonte["url"],
            "principal": self.principal,
        }
        if completo:
            dados.update({"verificada": self.verificada, "criterio_verificacao": self.criterio_verificacao,
                          "lugar_id": self.lugar_id, "id_externo": self.id_externo})
        return dados
