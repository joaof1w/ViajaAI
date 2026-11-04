"""Controller do recurso MensagemChat (assistente de IA "Vai")."""
from flask import Blueprint, g, jsonify, request

from backend.services.assistente_service import (
    ObterPermissoesAssistenteService,
    SalvarPermissoesAssistenteService,
)
from backend.services.enviar_mensagem_chat_service import EnviarMensagemChatService
from backend.services.listar_historico_chat_service import ListarHistoricoChatService
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar


class ChatController:
    prefixo = "/api/chat"

    def __init__(self):
        self.listar_historico_chat_service = ListarHistoricoChatService()
        self.enviar_mensagem_chat_service = EnviarMensagemChatService()
        self.obter_permissoes_assistente_service = ObterPermissoesAssistenteService()
        self.salvar_permissoes_assistente_service = SalvarPermissoesAssistenteService()

    def historico(self):
        return jsonify(self.listar_historico_chat_service.executar(g.usuario)), 200

    def enviar(self):
        dados = request.get_json(silent=True) or {}
        viagem_id = dados.get("viagem_id")
        viagem_id = int(viagem_id) if str(viagem_id or "").isdigit() else None
        resultado = self.enviar_mensagem_chat_service.executar(g.usuario, dados.get("texto"), viagem_id)
        return jsonify(resultado), 201

    def permissoes(self):
        return jsonify(self.obter_permissoes_assistente_service.executar(g.usuario)), 200

    def salvar_permissoes(self):
        dados = request.get_json(silent=True) or {}
        return jsonify(self.salvar_permissoes_assistente_service.executar(g.usuario, dados)), 200

    def registrar(self, app):
        bp = Blueprint("chat", __name__, url_prefix=self.prefixo)
        bp.add_url_rule("", view_func=login_obrigatorio(self.historico), methods=["GET"])
        bp.add_url_rule("", view_func=login_obrigatorio(limitar("chat", 20, 60)(self.enviar)), methods=["POST"])
        bp.add_url_rule("/permissoes", view_func=login_obrigatorio(self.permissoes), methods=["GET"])
        bp.add_url_rule("/permissoes", view_func=login_obrigatorio(self.salvar_permissoes), methods=["PUT"])
        app.register_blueprint(bp)
        return bp
