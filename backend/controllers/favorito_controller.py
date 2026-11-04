"""Controller do recurso Favorito (lugares salvos)."""
from flask import Blueprint, g, jsonify, request

from backend.services.listar_favoritos_service import ListarFavoritosService
from backend.services.remover_favorito_service import RemoverFavoritoService
from backend.services.salvar_favorito_service import SalvarFavoritoService
from backend.utils.autenticacao import login_obrigatorio


class FavoritoController:
    prefixo = "/api/favoritos"

    def __init__(self):
        self.listar_favoritos_service = ListarFavoritosService()
        self.salvar_favorito_service = SalvarFavoritoService()
        self.remover_favorito_service = RemoverFavoritoService()

    def listar(self):
        return jsonify(self.listar_favoritos_service.executar(g.usuario)), 200

    def salvar(self):
        dados = request.get_json(silent=True) or {}
        lugar_id = dados.get("lugar_id")
        return jsonify(self.salvar_favorito_service.executar(g.usuario, lugar_id)), 201

    def remover(self, lugar_id):
        return jsonify(self.remover_favorito_service.executar(g.usuario, lugar_id)), 200

    def registrar(self, app):
        bp = Blueprint("favoritos", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=login_obrigatorio(self.listar), methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(self.salvar), methods=["POST"])
        bp.add_url_rule(
            "/<int:lugar_id>", view_func=login_obrigatorio(self.remover), methods=["DELETE"]
        )
        app.register_blueprint(bp)
        return bp
