"""Controller do recurso Compromisso (calendário da viagem)."""
from flask import Blueprint, g, jsonify

from backend.services.calendario_service import (
    CriarCompromissoService,
    EditarCompromissoService,
    ExcluirCompromissoService,
    ObterCalendarioService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.requisicao import corpo_json


class CalendarioController:
    def __init__(self):
        self.obter_calendario_service = ObterCalendarioService()
        self.criar_compromisso_service = CriarCompromissoService()
        self.editar_compromisso_service = EditarCompromissoService()
        self.excluir_compromisso_service = ExcluirCompromissoService()

    def calendario(self, viagem_id):
        return jsonify(self.obter_calendario_service.executar(viagem_id, g.usuario)), 200

    def criar(self, viagem_id):
        return jsonify(self.criar_compromisso_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def editar(self, compromisso_id):
        return jsonify(self.editar_compromisso_service.executar(compromisso_id, g.usuario, corpo_json())), 200

    def excluir(self, compromisso_id):
        return jsonify(self.excluir_compromisso_service.executar(compromisso_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("calendario", __name__, url_prefix="/api")
        bp.add_url_rule("/viagens/<int:viagem_id>/calendario", view_func=login_obrigatorio(self.calendario),
                        methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/compromissos", view_func=login_obrigatorio(self.criar),
                        methods=["POST"])
        bp.add_url_rule("/compromissos/<int:compromisso_id>", view_func=login_obrigatorio(self.editar),
                        methods=["PUT", "PATCH"])
        bp.add_url_rule("/compromissos/<int:compromisso_id>", view_func=login_obrigatorio(self.excluir),
                        methods=["DELETE"])
        app.register_blueprint(bp)
        return bp
