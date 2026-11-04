"""Caso de uso: autenticar usuário (login com e-mail e senha)."""
from backend.models.usuario import Usuario
from backend.utils.erros import ErroDeNegocio, NaoAutorizado
from backend.utils.validadores import validar_email


class AutenticarUsuarioService:
    def executar(self, dados):
        email = validar_email(dados.get("email"))
        senha = dados.get("senha") or ""

        usuario = Usuario.buscar_por_email(email)
        if usuario is None or not usuario.conferir_senha(senha):
            # Mensagem genérica de propósito: não revela se o e-mail existe.
            raise NaoAutorizado("E-mail ou senha incorretos.")

        if not usuario.verificado:
            raise ErroDeNegocio(
                "Confirme o código enviado para o seu e-mail antes de entrar.",
                campo="email",
                status=403,
            )

        usuario.gerar_token()
        usuario.salvar()
        return {
            "token": usuario.token,
            "usuario": usuario.to_dict(incluir_preferencias=True),
            "possui_preferencias": usuario.preferencia is not None,
        }
