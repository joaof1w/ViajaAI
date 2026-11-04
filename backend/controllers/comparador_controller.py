"""Controller do Comparador de Destinos."""
from flask import Blueprint, jsonify, request

from backend.services.comparador_service import CompararDestinosService
from backend.utils.autenticacao import usuario_do_token
from backend.utils.erros import ErroDeValidacao
from backend.utils.limite_requisicoes import limitar


class ComparadorController:
    prefixo = "/api/comparador"

    def __init__(self):
        self.comparar_destinos_service = CompararDestinosService()

    def comparar(self):
        try:
            ids = [int(i) for i in (request.args.get("ids") or "").split(",") if i.strip()]
        except ValueError:
            raise ErroDeValidacao("Lista de destinos inválida.", campo="ids")
        return jsonify(self.comparar_destinos_service.executar(ids, usuario_do_token())), 200

    def registrar(self, app):
        bp = Blueprint("comparador", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=limitar("comparar", 30, 60)(self.comparar), methods=["GET"])
        app.register_blueprint(bp)
        return bp
