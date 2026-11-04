"""Controller do recurso MensagemChat (assistente de IA "Vai")."""
from flask import Blueprint, g, jsonify, request

from backend.services.enviar_mensagem_chat_service import EnviarMensagemChatService
from backend.services.listar_historico_chat_service import ListarHistoricoChatService
from backend.utils.autenticacao import login_obrigatorio


class ChatController:
    prefixo = "/api/chat"

    def __init__(self):
        self.listar_historico_chat_service = ListarHistoricoChatService()
        self.enviar_mensagem_chat_service = EnviarMensagemChatService()

    def historico(self):
        return jsonify(self.listar_historico_chat_service.executar(g.usuario)), 200

    def enviar(self):
        dados = request.get_json(silent=True) or {}
        resultado = self.enviar_mensagem_chat_service.executar(g.usuario, dados.get("texto"))
        return jsonify(resultado), 201

    def registrar(self, app):
        bp = Blueprint("chat", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=login_obrigatorio(self.historico), methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(self.enviar), methods=["POST"])
        app.register_blueprint(bp)
        return bp
