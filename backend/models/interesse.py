"""Entidade Interesse (catálogo: Praia, Gastronomia, Aventura, Cultura, Museus, Natureza)."""
from backend.extensions import db
from backend.models.base import ModeloBase

# Tabela associativa N:N entre a preferência do usuário e o catálogo de interesses
preferencia_interesses = db.Table(
    "preferencia_interesses",
    db.Column("preferencia_id", db.Integer, db.ForeignKey("preferencias.id"), primary_key=True),
    db.Column("interesse_id", db.Integer, db.ForeignKey("interesses.id"), primary_key=True),
)


class Interesse(db.Model, ModeloBase):
    __tablename__ = "interesses"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(60), nullable=False)
    icone = db.Column(db.String(10), nullable=False, default="✨")
    cor = db.Column(db.String(20), nullable=False, default="#f0f2f5")

    @classmethod
    def buscar_por_slug(cls, slug):
        return db.session.query(cls).filter(cls.slug == slug).first()

    @classmethod
    def buscar_por_slugs(cls, slugs):
        if not slugs:
            return []
        return db.session.query(cls).filter(cls.slug.in_(slugs)).all()

    def to_dict(self):
        return {"id": self.id, "slug": self.slug, "nome": self.nome, "icone": self.icone, "cor": self.cor}
