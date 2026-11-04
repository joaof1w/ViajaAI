"""Caso de uso: cadastrar usuário."""
from backend.config import Config
from backend.models.codigo_verificacao import CodigoVerificacao
from backend.models.usuario import Usuario
from backend.services.envio_email_service import EnvioEmailService
from backend.utils.erros import ConflitoDeDados
from backend.utils.validadores import validar_email, validar_nome, validar_senha


class CadastrarUsuarioService:
    """Valida os dados, cria o usuário e dispara o código de verificação."""

    def __init__(self, servico_email=None):
        self.servico_email = servico_email or EnvioEmailService()

    def executar(self, dados):
        nome = validar_nome(dados.get("nome"))
        email = validar_email(dados.get("email"))
        senha = validar_senha(dados.get("senha"), dados.get("confirmacao_senha"))

        existente = Usuario.buscar_por_email(email)
        if existente and existente.verificado:
            raise ConflitoDeDados("Este e-mail já está cadastrado. Faça login.", campo="email")

        if existente:  # cadastro iniciado e não concluído: reaproveita o registro
            usuario = existente
            usuario.nome = nome
            usuario.definir_senha(senha)
            usuario.salvar()
        else:
            usuario = Usuario(nome=nome, email=email, verificado=False)
            usuario.definir_senha(senha)
            usuario.salvar()

        codigo = CodigoVerificacao.emitir_para(usuario)
        self.servico_email.enviar_codigo(usuario, codigo.codigo)

        resposta = {
            "usuario": usuario.to_dict(),
            "mensagem": f"Enviamos um código de 6 dígitos para {usuario.email}.",
        }
        if Config.DEBUG and Config.EMAIL_MODO != "smtp":
            # Facilita o teste em desenvolvimento; nunca exposto em produção.
            resposta["codigo_debug"] = codigo.codigo
        return resposta
