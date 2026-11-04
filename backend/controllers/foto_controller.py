"""Controller das fotografias: fotos reais dos lugares, fundo da tela inicial e arquivos enviados."""
import os

from flask import Blueprint, abort, jsonify, request, send_from_directory

from backend.services.fotos_lugar_service import ListarFotosLugarService, ObterFundoInicialService
from backend.utils import arquivos


class FotoController:
    def __init__(self):
        self.listar_fotos_lugar_service = ListarFotosLugarService()
        self.obter_fundo_inicial_service = ObterFundoInicialService()

    def fotos_do_lugar(self, lugar_id):
        return jsonify(self.listar_fotos_lugar_service.executar(lugar_id)), 200

    def fundo_inicial(self):
        resposta = jsonify(self.obter_fundo_inicial_service.executar())
        resposta.headers["Cache-Control"] = "public, max-age=600"
        return resposta, 200

    def arquivo(self, subpasta, nome):
        """Serve uploads só com URL assinada e válida (gerada após checar permissão)."""
        if not arquivos.assinatura_valida(subpasta, nome, request.args.get("exp"), request.args.get("sig")):
            abort(404, description="Arquivo não encontrado.")
        pasta = arquivos.pasta(subpasta)
        if not os.path.isfile(os.path.join(pasta, nome)):
            abort(404, description="Arquivo não encontrado.")
        resposta = send_from_directory(pasta, nome, max_age=3600)
        resposta.headers["Cache-Control"] = "private, max-age=3600"
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        return resposta

    def registrar(self, app):
        bp = Blueprint("fotos", __name__, url_prefix="/api")
        bp.add_url_rule("/lugares/<int:lugar_id>/fotos", view_func=self.fotos_do_lugar, methods=["GET"])
        bp.add_url_rule("/vitrine/fundo", view_func=self.fundo_inicial, methods=["GET"])
        bp.add_url_rule("/arquivos/<subpasta>/<nome>", view_func=self.arquivo, methods=["GET"])
        app.register_blueprint(bp)
        return bp
