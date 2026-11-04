"""Caso de uso: reenviar o código de verificação."""
from backend.config import Config
from backend.models.codigo_verificacao import CodigoVerificacao
from backend.models.usuario import Usuario
from backend.services.envio_email_service import EnvioEmailService
from backend.utils.erros import ErroDeNegocio, NaoEncontrado
from backend.utils.validadores import validar_email


class ReenviarCodigoService:
    def __init__(self, servico_email=None):
        self.servico_email = servico_email or EnvioEmailService()

    def executar(self, dados):
        email = validar_email(dados.get("email"))
        usuario = Usuario.buscar_por_email(email)
        if usuario is None:
            raise NaoEncontrado("Não encontramos um cadastro com este e-mail.", campo="email")
        if usuario.verificado:
            raise ErroDeNegocio("Esta conta já está verificada.", campo="email")

        codigo = CodigoVerificacao.emitir_para(usuario)
        self.servico_email.enviar_codigo(usuario, codigo.codigo)

        resposta = {"mensagem": f"Novo código enviado para {usuario.email}."}
        if Config.DEBUG and Config.EMAIL_MODO != "smtp":
            resposta["codigo_debug"] = codigo.codigo
        return resposta
