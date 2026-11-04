"""Caso de uso: enviar uma mensagem ao assistente de IA e obter a resposta."""
from backend.models.mensagem_chat import MensagemChat
from backend.models.preferencia import FAIXAS_ORCAMENTO
from backend.services.assistente_service import MontarContextoAssistenteService, SugerirAcoesAssistenteService
from backend.services.gemini_service import GeminiService
from backend.services.listar_lugares_service import ListarLugaresService
from backend.services.recomendar_lugares_service import RecomendarLugaresService
from backend.utils.erros import ErroDeValidacao


class EnviarMensagemChatService:
    """Monta o contexto (perfil + dados autorizados pelo usuário) e consulta o Vai."""

    def __init__(self, servico_ia=None, servico_recomendacao=None, servico_listagem=None,
                 servico_contexto=None, servico_acoes=None):
        self.servico_ia = servico_ia or GeminiService()
        self.servico_recomendacao = servico_recomendacao or RecomendarLugaresService()
        self.servico_listagem = servico_listagem or ListarLugaresService()
        self.servico_contexto = servico_contexto or MontarContextoAssistenteService()
        self.servico_acoes = servico_acoes or SugerirAcoesAssistenteService()

    def executar(self, usuario, texto, viagem_id=None):
        texto = (texto or "").strip()
        if not texto:
            raise ErroDeValidacao("Escreva uma pergunta.", campo="texto")
        if len(texto) > 1000:
            raise ErroDeValidacao("Mensagem muito longa (máximo 1000 caracteres).", campo="texto")

        historico = [m.to_dict() for m in MensagemChat.listar_por_usuario(usuario.id, limite=20)]
        # Valida o acesso à viagem (404 se não participa) antes de registrar a pergunta.
        contexto = self._montar_contexto(usuario)
        contexto.update(self.servico_contexto.executar(usuario, viagem_id))
        MensagemChat(usuario_id=usuario.id, autor="usuario", texto=texto).salvar()

        resposta = self.servico_ia.executar(texto, contexto, historico)

        mensagem_ia = MensagemChat(
            usuario_id=usuario.id, autor="ia", texto=resposta["texto"]
        ).salvar()

        return {
            "resposta": mensagem_ia.to_dict(),
            "origem": resposta["origem"],
            "acoes": self.servico_acoes.executar(texto, contexto),
            "permissoes": contexto.get("permissoes"),
        }

    # ------------------------------------------------------------------
    def _montar_contexto(self, usuario):
        preferencia = usuario.preferencia
        if preferencia is not None:
            lugares = self.servico_recomendacao.executar(usuario, limite=8)["lugares"]
            faixa = FAIXAS_ORCAMENTO.get(preferencia.orcamento, FAIXAS_ORCAMENTO[2])
            interesses = [i.nome for i in preferencia.interesses]
            cidade, estado, rotulo = preferencia.cidade, preferencia.estado, faixa["rotulo"]
        else:
            lugares = self.servico_listagem.executar(usuario, limite=8)["lugares"]
            interesses, cidade, estado, rotulo = [], None, None, "Moderado"

        return {
            "nome": usuario.primeiro_nome,
            "cidade": cidade,
            "estado": estado,
            "interesses": interesses,
            "orcamento_rotulo": rotulo,
            "lugares": lugares,
        }
