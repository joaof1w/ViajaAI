"""Controller do recurso Preferencia (interesses, orçamento e localização)."""
from flask import Blueprint, g, jsonify, request

from backend.services.listar_interesses_service import ListarInteressesService
from backend.services.salvar_preferencias_service import SalvarPreferenciasService
from backend.utils.autenticacao import login_obrigatorio


class PreferenciaController:
    prefixo = "/api/preferencias"

    def __init__(self):
        self.listar_interesses_service = ListarInteressesService()
        self.salvar_preferencias_service = SalvarPreferenciasService()

    def opcoes(self):
        return jsonify(self.listar_interesses_service.executar()), 200

    def minhas(self):
        preferencia = g.usuario.preferencia
        return jsonify({"preferencias": preferencia.to_dict() if preferencia else None}), 200

    def salvar(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.salvar_preferencias_service.executar(g.usuario, dados)), 200

    def registrar(self, app):
        bp = Blueprint("preferencias", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("/opcoes", view_func=self.opcoes, methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(self.minhas), methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(self.salvar), methods=["PUT", "POST"])
        app.register_blueprint(bp)
        return bp
