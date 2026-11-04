"""Casos de uso das Viagens em Grupo (feature 7).

Participantes e convites:
    ListarParticipantesService · ConvidarParticipanteService · ListarConvitesService
    ResponderConviteService · AlterarPapelService · RemoverParticipanteService
Decisões do grupo:
    ListarSugestoesService · CriarSugestaoService · VotarSugestaoService · DecidirSugestaoService
"""
from backend.extensions import db
from backend.models.lugar import Lugar
from backend.models.roteiro import AtividadeRoteiro
from backend.models.sugestao import SugestaoViagem, VotoSugestao
from backend.models.usuario import Usuario
from backend.models.viagem import PAPEIS, ParticipanteViagem
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.services.envio_email_service import EnvioEmailService
from backend.services.roteiros_service import nova_versao_roteiro
from backend.utils.datas import agora_utc
from backend.utils.erros import AcessoNegado, ConflitoDeDados, ErroDeNegocio, ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import validar_email, validar_escolha, validar_inteiro, validar_texto

MAXIMO_PARTICIPANTES = 30


def _participantes(viagem, usuario):
    pode_gerenciar = viagem.proprietario_id == usuario.id
    itens = []
    for p in sorted(viagem.participantes, key=lambda x: (x.status != "aceito", x.criado_em)):
        if p.status == "recusado" and not pode_gerenciar:
            continue
        dados = p.to_dict()
        if not pode_gerenciar:
            dados["usuario"].pop("email", None)  # e-mails só para o organizador
        itens.append(dados)
    return {
        "proprietario": {"id": viagem.proprietario_id, "nome": viagem.proprietario.nome,
                         "iniciais": viagem.proprietario.iniciais},
        "participantes": itens,
        "papeis": [{"valor": k, "descricao": v} for k, v in PAPEIS.items()],
        "meu_papel": viagem.papel_de(usuario.id),
        "pode_gerenciar": pode_gerenciar,
    }


class ListarParticipantesService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        return _participantes(self.autorizacao.executar(viagem_id, usuario, "leitura"), usuario)


class ConvidarParticipanteService:
    def __init__(self, autorizacao=None, servico_email=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()
        self.servico_email = servico_email or EnvioEmailService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "proprietario")
        email = validar_email(dados.get("email"))
        papel = validar_escolha(dados.get("papel"), PAPEIS, "papel", "papel", padrao="viajante")
        convidado = Usuario.buscar_por_email(email)
        if convidado is None or not convidado.verificado:
            raise NaoEncontrado("Não há uma conta verificada no Viajaí com este e-mail.", campo="email")
        if convidado.id == viagem.proprietario_id:
            raise ErroDeValidacao("Você já é o organizador desta viagem.", campo="email")
        if sum(1 for p in viagem.participantes if p.status != "recusado") >= MAXIMO_PARTICIPANTES:
            raise ErroDeNegocio(f"Limite de {MAXIMO_PARTICIPANTES} participantes atingido.")
        existente = viagem.participante(convidado.id)
        if existente and existente.status in ("pendente", "aceito"):
            raise ConflitoDeDados("Esta pessoa já foi convidada.", campo="email")
        participante = existente or ParticipanteViagem(viagem_id=viagem.id, usuario_id=convidado.id)
        participante.papel, participante.status = papel, "pendente"
        participante.convidado_por_id, participante.criado_em, participante.respondido_em = usuario.id, agora_utc(), None
        participante.salvar()
        try:
            self.servico_email.executar(
                convidado.email, f"Convite para a viagem {viagem.titulo} · Viajaí",
                f"Olá, {convidado.primeiro_nome}!\n\n{usuario.nome} convidou você para a viagem "
                f"'{viagem.titulo}' ({viagem.destino}). Entre no Viajaí para aceitar ou recusar.",
            )
        except Exception as erro:  # o convite vale mesmo se o e-mail falhar
            print(f"[Convite] e-mail não enviado: {erro}", flush=True)
        db.session.refresh(viagem)
        return {"mensagem": f"Convite enviado para {convidado.nome}.", **_participantes(viagem, usuario)}


class ListarConvitesService:
    def executar(self, usuario):
        convites = ParticipanteViagem.convites_pendentes(usuario.id)
        return {"total": len(convites), "convites": [c.to_convite_dict() for c in convites]}


class ResponderConviteService:
    def executar(self, convite_id, usuario, aceitar):
        convite = ParticipanteViagem.buscar_por_id(convite_id)
        if convite is None or convite.usuario_id != usuario.id or convite.status != "pendente":
            raise NaoEncontrado("Convite não encontrado.")
        convite.status = "aceito" if aceitar else "recusado"
        convite.respondido_em = agora_utc()
        db.session.commit()
        if aceitar:
            return {"mensagem": f"Você agora participa de '{convite.viagem.titulo}'.", "viagem_id": convite.viagem_id}
        return {"mensagem": "Convite recusado.", "viagem_id": None}


def _participante_da_viagem(viagem, participante_id):
    participante = ParticipanteViagem.buscar_por_id(participante_id)
    if participante is None or participante.viagem_id != viagem.id:
        raise NaoEncontrado("Participante não encontrado.")
    return participante


class AlterarPapelService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, participante_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "proprietario")
        participante = _participante_da_viagem(viagem, participante_id)
        participante.papel = validar_escolha(dados.get("papel"), PAPEIS, "papel", "papel")
        db.session.commit()
        return {"mensagem": "Permissão atualizada.", **_participantes(viagem, usuario)}


class RemoverParticipanteService:
    """O organizador remove qualquer participante; um participante pode sair sozinho."""

    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, participante_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        participante = _participante_da_viagem(viagem, participante_id)
        if viagem.proprietario_id != usuario.id and participante.usuario_id != usuario.id:
            raise AcessoNegado("Somente o organizador pode remover outros participantes.")
        saiu = participante.usuario_id == usuario.id
        viagem.participantes.remove(participante)
        db.session.delete(participante)
        db.session.commit()
        if saiu:
            return {"mensagem": "Você saiu da viagem.", "saiu": True}
        return {"mensagem": "Participante removido.", "saiu": False, **_participantes(viagem, usuario)}


# ---------------------------------------------------------------------------
# Sugestões e votação
# ---------------------------------------------------------------------------
def _sugestoes(viagem, usuario):
    itens = sorted(viagem.sugestoes, key=lambda s: (s.status != "aberta", -len(s.votos), s.criado_em))
    return {
        "sugestoes": [s.to_dict(usuario.id) for s in itens],
        "pode_decidir": AutorizacaoViagemService.pode(viagem, usuario, "edicao"),
        "membros": len(viagem.membros_ids()),
    }


def _sugestao_autorizada(sugestao_id, usuario, autorizacao, nivel):
    sugestao = SugestaoViagem.buscar_por_id(sugestao_id)
    if sugestao is None:
        raise NaoEncontrado("Sugestão não encontrada.")
    autorizacao.executar(sugestao.viagem_id, usuario, nivel)
    return sugestao


class ListarSugestoesService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        return _sugestoes(self.autorizacao.executar(viagem_id, usuario, "leitura"), usuario)


class CriarSugestaoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        abertas = sum(1 for s in viagem.sugestoes if s.autor_id == usuario.id and s.status == "aberta")
        if abertas >= 20:
            raise ErroDeNegocio("Você já tem muitas sugestões abertas nesta viagem.")
        lugar_id = dados.get("lugar_id")
        lugar = Lugar.buscar_por_id(validar_inteiro(lugar_id, "lugar_id", "lugar", minimo=1)) if lugar_id else None
        if lugar_id and lugar is None:
            raise ErroDeValidacao("Lugar não encontrado.", campo="lugar_id")
        sugestao = SugestaoViagem(
            viagem_id=viagem.id, autor_id=usuario.id, lugar_id=lugar.id if lugar else None,
            titulo=validar_texto(dados.get("titulo") or (lugar.nome if lugar else None), "titulo", "a sugestão",
                                 minimo=2, maximo=160),
            descricao=validar_texto(dados.get("descricao"), "descricao", "a descrição", maximo=1000, obrigatorio=False),
        )
        sugestao.votos.append(VotoSugestao(usuario_id=usuario.id, valor=1))  # o autor apoia a própria ideia
        sugestao.salvar()
        db.session.refresh(viagem)
        return {"mensagem": "Sugestão enviada ao grupo.", **_sugestoes(viagem, usuario)}


class VotarSugestaoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, sugestao_id, usuario, dados):
        sugestao = _sugestao_autorizada(sugestao_id, usuario, self.autorizacao, "leitura")
        if sugestao.status != "aberta":
            raise ErroDeNegocio("A votação desta sugestão já foi encerrada.")
        valor = validar_inteiro(dados.get("valor"), "valor", "o voto", minimo=-1, maximo=1)
        voto = next((v for v in sugestao.votos if v.usuario_id == usuario.id), None)
        if valor == 0:
            if voto:
                sugestao.votos.remove(voto)
                db.session.delete(voto)
        elif voto:
            voto.valor = valor
        else:
            sugestao.votos.append(VotoSugestao(usuario_id=usuario.id, valor=valor))
        db.session.commit()
        return _sugestoes(sugestao.viagem, usuario)


class DecidirSugestaoService:
    """Organizador/editores aprovam (vira atividade do roteiro principal) ou rejeitam."""

    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, sugestao_id, usuario, dados):
        sugestao = _sugestao_autorizada(sugestao_id, usuario, self.autorizacao, "edicao")
        if sugestao.status != "aberta":
            raise ErroDeNegocio("Esta sugestão já foi decidida.")
        decisao = validar_escolha(dados.get("decisao"), ("aprovada", "rejeitada"), "decisao", "decisão")
        viagem = sugestao.viagem
        if decisao == "aprovada":
            dia = validar_inteiro(dados.get("dia") or 1, "dia", "o dia", minimo=1, maximo=viagem.duracao_dias)
            roteiro = viagem.roteiro_ativo or nova_versao_roteiro(viagem, usuario, "Roteiro do grupo", "manual")
            lugar = sugestao.lugar
            atividade = AtividadeRoteiro(
                dia=dia, ordem=max((a.ordem for a in roteiro.atividades if a.dia == dia), default=0) + 1,
                titulo=sugestao.titulo, descricao=sugestao.descricao or (lugar.descricao if lugar else None),
                categoria="atracao", lugar_id=lugar.id if lugar else None, fonte="sugestao",
                latitude=lugar.latitude if lugar else None, longitude=lugar.longitude if lugar else None,
            )
            roteiro.atividades.append(atividade)
            db.session.flush()
            sugestao.atividade_id = atividade.id
        sugestao.status, sugestao.decidido_por_id, sugestao.decidido_em = decisao, usuario.id, agora_utc()
        db.session.commit()
        mensagem = "Aprovada e adicionada ao roteiro!" if decisao == "aprovada" else "Sugestão rejeitada."
        return {"mensagem": mensagem, **_sugestoes(viagem, usuario)}
