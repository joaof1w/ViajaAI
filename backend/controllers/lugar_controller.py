"""Controller do recurso Lugar (destinos, restaurantes e experiências)."""
from flask import Blueprint, g, jsonify, request

from backend.services.buscar_lugares_service import BuscarLugaresService
from backend.services.listar_lugares_service import ListarLugaresService
from backend.services.obter_lugar_service import ObterLugarService
from backend.services.recomendar_lugares_service import RecomendarLugaresService
from backend.utils.autenticacao import login_obrigatorio, usuario_do_token


class LugarController:
    prefixo = "/api/lugares"

    def __init__(self):
        self.listar_lugares_service = ListarLugaresService()
        self.buscar_lugares_service = BuscarLugaresService()
        self.recomendar_lugares_service = RecomendarLugaresService()
        self.obter_lugar_service = ObterLugarService()

    # ---------------- ações ----------------
    def listar(self):
        usuario = usuario_do_token()  # autenticação opcional
        categoria = request.args.get("categoria")
        limite = request.args.get("limite", 60, type=int)
        return jsonify(self.listar_lugares_service.executar(usuario, categoria, limite)), 200

    def buscar(self):
        usuario = usuario_do_token()
        filtros = {
            "texto": request.args.get("q"),
            "categoria": request.args.get("categoria"),
            "preco_maximo": request.args.get("preco_maximo", type=int),
            "estado": request.args.get("estado"),
            "nota_minima": request.args.get("nota_minima", type=float),
            "ordenar": request.args.get("ordenar"),
            "limite": request.args.get("limite", 60, type=int),
        }
        return jsonify(self.buscar_lugares_service.executar(usuario, filtros)), 200

    def recomendacoes(self):
        limite = request.args.get("limite", 8, type=int)
        categoria = request.args.get("categoria")
        resultado = self.recomendar_lugares_service.executar(g.usuario, limite, categoria)
        return jsonify(resultado), 200

    def detalhar(self, lugar_id):
        usuario = usuario_do_token()
        return jsonify(self.obter_lugar_service.executar(lugar_id, usuario)), 200

    # ---------------- rotas ----------------
    def registrar(self, app):
        bp = Blueprint("lugares", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=self.listar, methods=["GET"])
        bp.add_url_rule("/busca", view_func=self.buscar, methods=["GET"])
        bp.add_url_rule(
            "/recomendacoes", view_func=login_obrigatorio(self.recomendacoes), methods=["GET"]
        )
        bp.add_url_rule("/<int:lugar_id>", view_func=self.detalhar, methods=["GET"])
        app.register_blueprint(bp)
        return bp
