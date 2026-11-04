"""Controller do recurso ItemChecklist (checklist inteligente da viagem)."""
from flask import Blueprint, g, jsonify

from backend.services.checklist_service import (
    AdicionarItemChecklistService,
    AtualizarItemChecklistService,
    GerarSugestoesChecklistService,
    ImportarChecklistService,
    ListarChecklistService,
    RemoverItemChecklistService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.requisicao import corpo_json


class ChecklistController:
    def __init__(self):
        self.listar_checklist_service = ListarChecklistService()
        self.gerar_sugestoes_checklist_service = GerarSugestoesChecklistService()
        self.adicionar_item_checklist_service = AdicionarItemChecklistService()
        self.atualizar_item_checklist_service = AtualizarItemChecklistService()
        self.remover_item_checklist_service = RemoverItemChecklistService()
        self.importar_checklist_service = ImportarChecklistService()

    def listar(self, viagem_id):
        return jsonify(self.listar_checklist_service.executar(viagem_id, g.usuario)), 200

    def sugerir(self, viagem_id):
        return jsonify(self.gerar_sugestoes_checklist_service.executar(viagem_id, g.usuario)), 200

    def adicionar(self, viagem_id):
        return jsonify(self.adicionar_item_checklist_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def importar(self, viagem_id):
        return jsonify(self.importar_checklist_service.executar(viagem_id, g.usuario, corpo_json())), 200

    def atualizar(self, item_id):
        return jsonify(self.atualizar_item_checklist_service.executar(item_id, g.usuario, corpo_json())), 200

    def remover(self, item_id):
        return jsonify(self.remover_item_checklist_service.executar(item_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("checklist", __name__, url_prefix="/api")
        bp.add_url_rule("/viagens/<int:viagem_id>/checklist", view_func=login_obrigatorio(self.listar), methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/checklist", view_func=login_obrigatorio(self.adicionar),
                        methods=["POST"])
        bp.add_url_rule("/viagens/<int:viagem_id>/checklist/sugestoes", view_func=login_obrigatorio(self.sugerir),
                        methods=["POST"])
        bp.add_url_rule("/viagens/<int:viagem_id>/checklist/importar", view_func=login_obrigatorio(self.importar),
                        methods=["POST"])
        bp.add_url_rule("/checklist/<int:item_id>", view_func=login_obrigatorio(self.atualizar), methods=["PATCH", "PUT"])
        bp.add_url_rule("/checklist/<int:item_id>", view_func=login_obrigatorio(self.remover), methods=["DELETE"])
        app.register_blueprint(bp)
        return bp
