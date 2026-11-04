"""Caso de uso: listar o histórico de conversa com o assistente."""
from backend.models.mensagem_chat import MensagemChat


class ListarHistoricoChatService:
    SAUDACAO = (
        "Olá! Sou o Vai, seu assistente de viagem inteligente. 🌎 "
        "Com base no seu perfil, já preparei ótimas sugestões! Como posso te ajudar hoje?"
    )

    def executar(self, usuario):
        mensagens = MensagemChat.listar_por_usuario(usuario.id)
        if not mensagens:
            inicial = MensagemChat(
                usuario_id=usuario.id, autor="ia", texto=self.SAUDACAO
            ).salvar()
            mensagens = [inicial]
        return {
            "total": len(mensagens),
            "mensagens": [m.to_dict() for m in mensagens],
            "sugestoes": ["Sugerir roteiro", "Melhores épocas", "Ver preços"],
        }
