"""Caso de uso: listar o catálogo de interesses e as faixas de orçamento."""
from backend.models.interesse import Interesse
from backend.models.preferencia import FAIXAS_ORCAMENTO
from backend.utils.geo import listar_cidades


class ListarInteressesService:
    def executar(self):
        return {
            "interesses": [i.to_dict() for i in Interesse.listar_todos()],
            "orcamentos": [
                {"valor": valor, **dados} for valor, dados in sorted(FAIXAS_ORCAMENTO.items())
            ],
            "cidades": listar_cidades(),
        }
