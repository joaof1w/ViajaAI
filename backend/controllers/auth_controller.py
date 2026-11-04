"""Controller do recurso de autenticação: cadastro, verificação e login."""
from flask import Blueprint, g, jsonify, request

from backend.services.autenticar_usuario_service import AutenticarUsuarioService
from backend.services.cadastrar_usuario_service import CadastrarUsuarioService
from backend.services.encerrar_sessao_service import EncerrarSessaoService
from backend.services.reenviar_codigo_service import ReenviarCodigoService
from backend.services.verificar_codigo_service import VerificarCodigoService
from backend.utils.autenticacao import login_obrigatorio


class AuthController:
    """Recebe a requisição, chama o Service e devolve a resposta HTTP."""

    prefixo = "/api/auth"

    def __init__(self):
        self.cadastrar_usuario_service = CadastrarUsuarioService()
        self.verificar_codigo_service = VerificarCodigoService()
        self.reenviar_codigo_service = ReenviarCodigoService()
        self.autenticar_usuario_service = AutenticarUsuarioService()
        self.encerrar_sessao_service = EncerrarSessaoService()

    # ---------------- ações ----------------
    def cadastrar(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.cadastrar_usuario_service.executar(dados)), 201

    def verificar(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.verificar_codigo_service.executar(dados)), 200

    def reenviar_codigo(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.reenviar_codigo_service.executar(dados)), 200

    def login(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.autenticar_usuario_service.executar(dados)), 200

    def logout(self):
        return jsonify(self.encerrar_sessao_service.executar(g.usuario)), 200

    # ---------------- rotas ----------------
    def registrar(self, app):
        bp = Blueprint("auth", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("/cadastro", view_func=self.cadastrar, methods=["POST"])
        bp.add_url_rule("/verificar", view_func=self.verificar, methods=["POST"])
        bp.add_url_rule("/reenviar-codigo", view_func=self.reenviar_codigo, methods=["POST"])
        bp.add_url_rule("/login", view_func=self.login, methods=["POST"])
        bp.add_url_rule("/logout", view_func=login_obrigatorio(self.logout), methods=["POST"])
        app.register_blueprint(bp)
        return bp
