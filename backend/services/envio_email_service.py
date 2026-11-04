"""Integração externa: envio do e-mail com o código de verificação.

Encapsula o serviço externo (SMTP). Em modo "console" apenas registra no terminal,
o que permite testar o cadastro sem configurar servidor de e-mail.
"""
import smtplib
from email.message import EmailMessage

from backend.config import Config


class EnvioEmailService:
    """Caso de uso: enviar um e-mail transacional."""

    def __init__(self, config=None):
        self.config = config or Config

    def executar(self, destinatario, assunto, corpo):
        if self.config.EMAIL_MODO != "smtp" or not self.config.SMTP_HOST:
            print("\n" + "=" * 58)
            print(f"[Viajaí] E-mail simulado para {destinatario}")
            print(f"Assunto: {assunto}")
            print(corpo)
            print("=" * 58 + "\n", flush=True)
            return {"enviado": False, "modo": "console"}

        mensagem = EmailMessage()
        mensagem["From"] = self.config.EMAIL_REMETENTE
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        mensagem.set_content(corpo)

        with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORTA, timeout=15) as servidor:
            servidor.starttls()
            if self.config.SMTP_USUARIO:
                servidor.login(self.config.SMTP_USUARIO, self.config.SMTP_SENHA)
            servidor.send_message(mensagem)
        return {"enviado": True, "modo": "smtp"}

    def enviar_codigo(self, usuario, codigo):
        corpo = (
            f"Olá, {usuario.primeiro_nome}!\n\n"
            f"Seu código de verificação do Viajaí é: {codigo}\n\n"
            f"Ele expira em {self.config.CODIGO_VALIDADE_MINUTOS} minutos.\n"
            "Se não foi você quem pediu, ignore este e-mail."
        )
        return self.executar(usuario.email, "Seu código de verificação · Viajaí", corpo)
