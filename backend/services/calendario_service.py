"""Casos de uso do Calendário de Viagem (feature 9).

    ObterCalendarioService · CriarCompromissoService · EditarCompromissoService
    ExcluirCompromissoService

O calendário une os compromissos (reservas, transportes, passeios) às atividades do
roteiro principal que têm horário — integração automática, sem duplicar dados — e
aponta conflitos de horário entre eles.
"""
from datetime import datetime, timedelta

from backend.extensions import db
from backend.models.compromisso import TIPOS_COMPROMISSO, Compromisso
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.utils.erros import ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import (
    validar_coordenadas,
    validar_data_hora,
    validar_escolha,
    validar_inteiro,
    validar_texto,
)

DURACAO_PADRAO_ATIVIDADE = 60


def detectar_conflitos(eventos):
    """Pares de eventos cujos intervalos se sobrepõem (ordenados por início)."""
    ordenados = sorted(eventos, key=lambda e: e["_inicio"])
    conflitos = []
    for i, atual in enumerate(ordenados):
        for proximo in ordenados[i + 1:]:
            if proximo["_inicio"] >= atual["_fim"]:
                break
            conflitos.append([atual["chave"], proximo["chave"]])
    return conflitos


class ObterCalendarioService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        eventos, sem_horario = [], []
        for compromisso in viagem.compromissos:
            evento = compromisso.to_dict()
            evento.update(chave=f"c{compromisso.id}", origem="agenda", _inicio=compromisso.inicio, _fim=compromisso.fim)
            eventos.append(evento)
        roteiro = viagem.roteiro_ativo
        if roteiro is not None:
            for atividade in roteiro.atividades:
                data = viagem.data_do_dia(atividade.dia)
                if not atividade.horario:
                    sem_horario.append({**atividade.to_dict(), "data": data.isoformat(), "origem": "roteiro"})
                    continue
                hora, minuto = map(int, atividade.horario.split(":"))
                inicio = datetime(data.year, data.month, data.day, hora, minuto)
                duracao = atividade.duracao_min or DURACAO_PADRAO_ATIVIDADE
                fim = inicio + timedelta(minutes=duracao)
                eventos.append({
                    "chave": f"a{atividade.id}", "id": atividade.id, "origem": "roteiro", "titulo": atividade.titulo,
                    "tipo": atividade.categoria, "tipo_rotulo": atividade.to_dict()["categoria_rotulo"], "icone": "🧭",
                    "inicio": inicio.isoformat(timespec="minutes"), "fim": fim.isoformat(timespec="minutes"),
                    "duracao_min": duracao, "local": atividade.endereco, "observacoes": atividade.descricao,
                    "horario_sugerido": atividade.horario_sugerido, "latitude": atividade.latitude,
                    "longitude": atividade.longitude, "_inicio": inicio, "_fim": fim,
                })
        conflitos = detectar_conflitos(eventos)
        em_conflito = {chave for par in conflitos for chave in par}
        eventos.sort(key=lambda e: e["_inicio"])
        for evento in eventos:
            evento["conflito"] = evento["chave"] in em_conflito
            evento.pop("_inicio"), evento.pop("_fim")
        dias = [(viagem.data_ida + timedelta(days=i)).isoformat() for i in range(viagem.duracao_dias)]
        return {
            "dias": dias,
            "eventos": eventos,
            "sem_horario": sem_horario,
            "conflitos": conflitos,
            "tipos": [{"valor": k, **v} for k, v in TIPOS_COMPROMISSO.items()],
            "roteiro_ativo": {"id": roteiro.id, "versao": roteiro.versao} if roteiro else None,
            "pode_editar": AutorizacaoViagemService.pode(viagem, usuario, "edicao"),
        }


def _validar(dados, viagem, atual=None):
    def valor(campo):
        return dados[campo] if campo in dados else (getattr(atual, campo) if atual else None)

    inicio = validar_data_hora(valor("inicio"), "inicio", "o início")
    limite_inicio = datetime.combine(viagem.data_ida, datetime.min.time()) - timedelta(days=1)
    limite_fim = datetime.combine(viagem.data_volta, datetime.max.time()) + timedelta(days=1)
    if not limite_inicio <= inicio <= limite_fim:
        raise ErroDeValidacao("O compromisso precisa estar dentro do período da viagem (±1 dia).", campo="inicio")
    lat, lon = validar_coordenadas(valor("latitude"), valor("longitude"))
    return {
        "titulo": validar_texto(valor("titulo"), "titulo", "o título", minimo=2, maximo=160),
        "tipo": validar_escolha(valor("tipo"), TIPOS_COMPROMISSO, "tipo", "tipo", padrao="outro"),
        "inicio": inicio,
        "duracao_min": validar_inteiro(valor("duracao_min") or 60, "duracao_min", "a duração (min)", minimo=5,
                                       maximo=7 * 24 * 60),
        "local": validar_texto(valor("local"), "local", "o local", maximo=200, obrigatorio=False),
        "observacoes": validar_texto(valor("observacoes"), "observacoes", "as observações", maximo=1500,
                                     obrigatorio=False),
        "latitude": lat, "longitude": lon,
    }


def _compromisso_autorizado(compromisso_id, usuario, autorizacao):
    compromisso = Compromisso.buscar_por_id(compromisso_id)
    if compromisso is None:
        raise NaoEncontrado("Compromisso não encontrado.")
    autorizacao.executar(compromisso.viagem_id, usuario, "edicao")
    return compromisso


class CriarCompromissoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        compromisso = Compromisso(viagem_id=viagem.id, criado_por_id=usuario.id, **_validar(dados, viagem))
        compromisso.salvar()
        return {"mensagem": "Compromisso adicionado à agenda.", "compromisso": compromisso.to_dict()}


class EditarCompromissoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, compromisso_id, usuario, dados):
        compromisso = _compromisso_autorizado(compromisso_id, usuario, self.autorizacao)
        for chave, valor in _validar(dados, compromisso.viagem, atual=compromisso).items():
            setattr(compromisso, chave, valor)
        db.session.commit()
        return {"mensagem": "Compromisso atualizado.", "compromisso": compromisso.to_dict()}


class ExcluirCompromissoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, compromisso_id, usuario):
        compromisso = _compromisso_autorizado(compromisso_id, usuario, self.autorizacao)
        compromisso.deletar()
        return {"mensagem": "Compromisso excluído.", "compromisso_id": compromisso_id}
