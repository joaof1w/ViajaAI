"""Exceções de domínio usadas pelos Services e traduzidas em HTTP pelas Controllers."""


class ErroDeAplicacao(Exception):
    status = 400

    def __init__(self, mensagem, campo=None, status=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo
        if status:
            self.status = status

    def to_dict(self):
        corpo = {"erro": self.mensagem}
        if self.campo:
            corpo["campo"] = self.campo
        return corpo


class ErroDeValidacao(ErroDeAplicacao):
    status = 422


class ErroDeNegocio(ErroDeAplicacao):
    status = 400


class NaoAutorizado(ErroDeAplicacao):
    status = 401


class NaoEncontrado(ErroDeAplicacao):
    status = 404


class ConflitoDeDados(ErroDeAplicacao):
    status = 409
