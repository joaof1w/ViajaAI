"""Fábrica da aplicação Flask: registra extensões, Controllers e o frontend."""
import os
from contextlib import contextmanager
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, send_from_directory
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
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

    # Em produção a chave padrão de desenvolvimento assinaria sessões e URLs de fotos de forma previsível.
    if not app.config.get("DEBUG") and not app.config.get("TESTING") \
            and app.config.get("SECRET_KEY") == "viajai-chave-de-desenvolvimento":
        raise RuntimeError("Defina SECRET_KEY no ambiente antes de rodar com FLASK_DEBUG=0.")

    db.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    registrar_controllers(app)
    registrar_tratadores_de_erro(app)
    registrar_cabecalhos_de_seguranca(app)
    registrar_frontend(app)

    with app.app_context():
        import backend.models  # noqa: F401  (garante o registro das tabelas)
        from backend.migracoes import aplicar_migracoes
        from backend.seeds import popular_banco

        # Vários workers (gunicorn) sobem juntos: o bloqueio evita criar tabelas/dados em paralelo.
        with _bloqueio_de_inicializacao():
            db.create_all()  # só cria tabelas ausentes; nunca altera ou apaga dados existentes
            aplicar_migracoes()
            popular_banco()

    iniciar_sincronizacao_de_fotos(app)
    return app


@contextmanager
def _bloqueio_de_inicializacao():
    """Exclusão mútua entre processos na mesma máquina (fcntl; sem efeito no Windows)."""
    try:
        import fcntl
    except ImportError:  # Windows: o servidor de desenvolvimento usa um único processo
        yield
        return
    caminho = os.path.join(BASE_DIR, "backend", ".inicializacao.lock")
    with open(caminho, "w") as arquivo:
        fcntl.flock(arquivo, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(arquivo, fcntl.LOCK_UN)


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(conexao, _registro):
    """SQLite só respeita integridade referencial (ON DELETE...) com esta pragma."""
    if conexao.__class__.__module__.startswith("sqlite3"):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def iniciar_sincronizacao_de_fotos(app):
    """Busca fotos reais (Wikimedia) em segundo plano para lugares ainda sem foto."""
    config = app.config
    if not (config.get("FOTOS_SINCRONIZACAO_AUTOMATICA") and config.get("INTEGRACOES_EXTERNAS")) or app.testing:
        return
    # Com o recarregador do Flask em modo debug, roda só no processo que atende requisições.
    if config.get("DEBUG") and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    from backend.services.fotos_lugar_service import sincronizar_em_segundo_plano

    sincronizar_em_segundo_plano(app)


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

    @app.errorhandler(RequestEntityTooLarge)
    def arquivo_grande(_erro):
        return jsonify({"erro": "Envio grande demais. Reduza o tamanho ou a quantidade de fotos.",
                        "campo": "fotos"}), 413

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        return jsonify({"erro": erro.description}), erro.code

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        app.logger.exception(erro)
        return jsonify({"erro": "Erro interno no servidor."}), 500


def registrar_cabecalhos_de_seguranca(app):
    hosts_tiles = urlparse(app.config.get("MAPA_TILE_URL", "")).netloc.replace("{s}.", "*.")
    imagens = " ".join(filter(None, [
        "'self' data: blob:", "https://upload.wikimedia.org", "https://images.pexels.com",
        "https://images.unsplash.com", "https://*.tile.openstreetmap.org",
        f"https://{hosts_tiles}" if hosts_tiles else "",
    ]))
    politica = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        f"img-src {imagens}; connect-src 'self'; font-src 'self'; object-src 'none'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resposta.headers.setdefault("Permissions-Policy", "geolocation=(), camera=(), microphone=()")
        if resposta.mimetype == "text/html":
            resposta.headers.setdefault("Content-Security-Policy", politica)
        return resposta


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
