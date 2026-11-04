"""Controller do recurso Usuario."""
from flask import Blueprint, g, jsonify

from backend.services.obter_perfil_service import ObterPerfilService
from backend.utils.autenticacao import login_obrigatorio


class UsuarioController:
    prefixo = "/api/usuarios"

    def __init__(self):
        self.obter_perfil_service = ObterPerfilService()

    def perfil(self):
        return jsonify(self.obter_perfil_service.executar(g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("usuarios", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("/eu", view_func=login_obrigatorio(self.perfil), methods=["GET"])
        app.register_blueprint(bp)
        return bp
