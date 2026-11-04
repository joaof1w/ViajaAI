"""Caso de uso transversal: garantir que o usuário pode acessar/alterar uma viagem.

Níveis (cumulativos):
    leitura      → proprietário e participantes que aceitaram o convite
    edicao       → proprietário e participantes com papel "editor"
    proprietario → somente quem criou a viagem

Quem não participa recebe 404 (não revela que a viagem existe); quem participa sem o
nível necessário recebe 403.
"""
from backend.models.viagem import Viagem
from backend.utils.erros import AcessoNegado, NaoEncontrado

NIVEIS = {
    "leitura": {"proprietario", "editor", "viajante"},
    "edicao": {"proprietario", "editor"},
    "proprietario": {"proprietario"},
}

MENSAGENS = {
    "edicao": "Somente o organizador e os editores podem alterar esta viagem.",
    "proprietario": "Somente o organizador da viagem pode fazer isso.",
}


class AutorizacaoViagemService:
    def executar(self, viagem_id, usuario, nivel="leitura"):
        viagem = Viagem.buscar_por_id(viagem_id)
        papel = viagem.papel_de(usuario.id) if viagem else None
        if viagem is None or papel in (None, "convidado"):
            raise NaoEncontrado("Viagem não encontrada.")
        if papel not in NIVEIS[nivel]:
            raise AcessoNegado(MENSAGENS.get(nivel, "Acesso negado."))
        return viagem

    @staticmethod
    def pode(viagem, usuario, nivel):
        return viagem.papel_de(usuario.id) in NIVEIS[nivel]
