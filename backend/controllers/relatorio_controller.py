"""Controller de relatórios (ranking de destinos e estatísticas)."""
from flask import Blueprint, jsonify, request

from backend.services.gerar_relatorio_service import GerarRelatorioService


class RelatorioController:
    prefixo = "/api/relatorios"

    def __init__(self):
        self.gerar_relatorio_service = GerarRelatorioService()

    def destinos(self):
        limite = request.args.get("limite", 10, type=int)
        return jsonify(self.gerar_relatorio_service.executar(limite)), 200

    def registrar(self, app):
        bp = Blueprint("relatorios", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("/destinos", view_func=self.destinos, methods=["GET"])
        app.register_blueprint(bp)
        return bp
