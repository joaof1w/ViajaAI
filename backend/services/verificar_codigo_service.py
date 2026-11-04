"""Caso de uso: verificar o código enviado por e-mail e ativar a conta."""
from backend.models.codigo_verificacao import CodigoVerificacao
from backend.models.usuario import Usuario
from backend.utils.erros import ErroDeNegocio, NaoEncontrado
from backend.utils.validadores import validar_codigo, validar_email


class VerificarCodigoService:
    def executar(self, dados):
        email = validar_email(dados.get("email"))
        codigo = validar_codigo(dados.get("codigo"))

        usuario = Usuario.buscar_por_email(email)
        if usuario is None:
            raise NaoEncontrado("Não encontramos um cadastro com este e-mail.", campo="email")
        if usuario.verificado:
            raise ErroDeNegocio("Esta conta já foi verificada. Faça login.", campo="email")

        registro = CodigoVerificacao.buscar_valido(usuario.id, codigo)
        if registro is None:
            raise ErroDeNegocio("Código inválido ou expirado.", campo="codigo")

        registro.marcar_como_usado()
        usuario.verificado = True
        usuario.gerar_token()
        usuario.salvar()

        return {
            "token": usuario.token,
            "usuario": usuario.to_dict(incluir_preferencias=True),
            "mensagem": "Conta verificada com sucesso!",
        }
