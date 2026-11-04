"""Fábrica da aplicação Flask: registra extensões, Controllers e o frontend."""
import os

from flask import Flask, abort, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.utils import safe_join

from backend.config import BASE_DIR, Config
from backend.controllers import CONTROLLERS
from backend.extensions import cors, db
from backend.utils.erros import ErroDeAplicacao

PASTA_FRONTEND = os.path.join(BASE_DIR, "frontend")


def create_app(config=Config):
    # O frontend é servido pelas rotas de registrar_frontend(), por isso static_folder=None.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)

    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    registrar_controllers(app)
    registrar_tratadores_de_erro(app)
    registrar_frontend(app)

    with app.app_context():
        import backend.models  # noqa: F401  (garante o registro das tabelas)
        from backend.seeds import popular_banco

        db.create_all()
        popular_banco()

    return app


def registrar_controllers(app):
    """Cada Controller é uma classe responsável por um recurso do sistema."""
    for classe in CONTROLLERS:
        classe().registrar(app)

    @app.get("/api/saude")
    def saude():
        return jsonify({"status": "ok", "app": "Viajaí"}), 200


def registrar_tratadores_de_erro(app):
    @app.errorhandler(ErroDeAplicacao)
    def erro_de_aplicacao(erro):
        return jsonify(erro.to_dict()), erro.status

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        return jsonify({"erro": erro.description}), erro.code

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        app.logger.exception(erro)
        return jsonify({"erro": "Erro interno no servidor."}), 500


def registrar_frontend(app):
    """Serve o frontend estático na mesma origem da API."""

    @app.get("/")
    def inicio():
        return send_from_directory(PASTA_FRONTEND, "index.html")

    @app.get("/<path:caminho>")
    def paginas(caminho):
        if caminho.startswith("api/"):
            abort(404, description="Rota de API inexistente.")
        destino = safe_join(PASTA_FRONTEND, caminho)
        if destino and os.path.isfile(destino):
            return send_from_directory(PASTA_FRONTEND, caminho)
        if destino and os.path.isfile(destino + ".html"):
            return send_from_directory(PASTA_FRONTEND, caminho + ".html")
        return send_from_directory(PASTA_FRONTEND, "index.html")
