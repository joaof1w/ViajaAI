"""Controller do recurso Viagem (planejador de viagens)."""
from flask import Blueprint, g, jsonify, request

from backend.services.viagens_service import (
    CriarViagemService,
    EditarViagemService,
    ExcluirViagemService,
    ListarViagensService,
    ObterViagemService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar
from backend.utils.requisicao import corpo_json


class ViagemController:
    prefixo = "/api/viagens"

    def __init__(self):
        self.listar_viagens_service = ListarViagensService()
        self.criar_viagem_service = CriarViagemService()
        self.obter_viagem_service = ObterViagemService()
        self.editar_viagem_service = EditarViagemService()
        self.excluir_viagem_service = ExcluirViagemService()

    def listar(self):
        return jsonify(self.listar_viagens_service.executar(g.usuario, request.args.get("status"))), 200

    def criar(self):
        return jsonify(self.criar_viagem_service.executar(g.usuario, corpo_json())), 201

    def detalhar(self, viagem_id):
        return jsonify(self.obter_viagem_service.executar(viagem_id, g.usuario)), 200

    def editar(self, viagem_id):
        return jsonify(self.editar_viagem_service.executar(viagem_id, g.usuario, corpo_json())), 200

    def excluir(self, viagem_id):
        return jsonify(self.excluir_viagem_service.executar(viagem_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("viagens", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=login_obrigatorio(self.listar), methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(limitar("criar_viagem", 30, 3600)(self.criar)), methods=["POST"])
        bp.add_url_rule("/<int:viagem_id>", view_func=login_obrigatorio(self.detalhar), methods=["GET"])
        bp.add_url_rule("/<int:viagem_id>", view_func=login_obrigatorio(self.editar), methods=["PUT", "PATCH"])
        bp.add_url_rule("/<int:viagem_id>", view_func=login_obrigatorio(self.excluir), methods=["DELETE"])
        app.register_blueprint(bp)
        return bp
