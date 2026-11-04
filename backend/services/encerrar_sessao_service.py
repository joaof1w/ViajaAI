"""Caso de uso: encerrar a sessão (logout)."""


class EncerrarSessaoService:
    def executar(self, usuario):
        usuario.token = None
        usuario.salvar()
        return {"mensagem": "Sessão encerrada."}
