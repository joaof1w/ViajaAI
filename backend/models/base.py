"""Operações básicas de persistência que permanecem na própria Model."""
from backend.extensions import db


class ModeloBase:
    """Mixin com o CRUD convencional herdado por todas as Models."""

    def salvar(self):
        db.session.add(self)
        db.session.commit()
        return self

    def atualizar(self, **campos):
        for chave, valor in campos.items():
            if valor is not None and hasattr(self, chave):
                setattr(self, chave, valor)
        db.session.commit()
        return self

    def deletar(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def listar_todos(cls):
        return db.session.query(cls).all()

    @classmethod
    def buscar_por_id(cls, identificador):
        if identificador in (None, ""):
            return None
        return db.session.get(cls, identificador)

    @classmethod
    def contar(cls):
        return db.session.query(cls).count()
