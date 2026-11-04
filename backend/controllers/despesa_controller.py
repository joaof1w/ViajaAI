"""Controller do recurso Despesa (planejamento financeiro da viagem)."""
from flask import Blueprint, g, jsonify

from backend.services.financas_service import (
    DefinirOrcamentoService,
    EditarDespesaService,
    ExcluirDespesaService,
    RegistrarDespesaService,
    ResumoFinanceiroService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.requisicao import corpo_json


class DespesaController:
    def __init__(self):
        self.resumo_financeiro_service = ResumoFinanceiroService()
        self.definir_orcamento_service = DefinirOrcamentoService()
        self.registrar_despesa_service = RegistrarDespesaService()
        self.editar_despesa_service = EditarDespesaService()
        self.excluir_despesa_service = ExcluirDespesaService()

    def resumo(self, viagem_id):
        return jsonify(self.resumo_financeiro_service.executar(viagem_id, g.usuario)), 200

    def orcamento(self, viagem_id):
        return jsonify(self.definir_orcamento_service.executar(viagem_id, g.usuario, corpo_json())), 200

    def registrar_despesa(self, viagem_id):
        return jsonify(self.registrar_despesa_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def editar(self, despesa_id):
        return jsonify(self.editar_despesa_service.executar(despesa_id, g.usuario, corpo_json())), 200

    def excluir(self, despesa_id):
        return jsonify(self.excluir_despesa_service.executar(despesa_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("despesas", __name__, url_prefix="/api")
        bp.add_url_rule("/viagens/<int:viagem_id>/financas", view_func=login_obrigatorio(self.resumo), methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/orcamento", view_func=login_obrigatorio(self.orcamento),
                        methods=["PUT"])
        bp.add_url_rule("/viagens/<int:viagem_id>/despesas", view_func=login_obrigatorio(self.registrar_despesa),
                        methods=["POST"])
        bp.add_url_rule("/despesas/<int:despesa_id>", view_func=login_obrigatorio(self.editar), methods=["PUT", "PATCH"])
        bp.add_url_rule("/despesas/<int:despesa_id>", view_func=login_obrigatorio(self.excluir), methods=["DELETE"])
        app.register_blueprint(bp)
        return bp
