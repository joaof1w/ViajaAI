"""Casos de uso de Avaliações e Experiências (feature 8).

    ListarAvaliacoesLugarService · CriarAvaliacaoService · EditarAvaliacaoService
    ExcluirAvaliacaoService · AdicionarFotosAvaliacaoService · RemoverFotoAvaliacaoService
    ListarComunidadeService

Proteções contra manipulação: uma avaliação por pessoa e lugar (constraint única),
só contas verificadas (login exige verificação), limite de publicações por hora e
média calculada apenas com as avaliações reais da comunidade (separada da nota do
catálogo). "Experiência verificada" = o autor tem, no Viajaí, uma viagem concluída
que passou pelo lugar.
"""
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.models.avaliacao import Avaliacao, FotoAvaliacao
from backend.models.diario import RegistroDiario
from backend.models.lugar import Lugar
from backend.repositories.viagem_repository import ViagemRepository
from backend.utils import arquivos
from backend.utils.datas import hoje
from backend.utils.erros import ConflitoDeDados, ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import validar_data, validar_inteiro, validar_texto
from backend.config import Config


def _lugar(lugar_id):
    lugar = Lugar.buscar_por_id(lugar_id)
    if lugar is None:
        raise NaoEncontrado("Lugar não encontrado.")
    return lugar


def _validar(dados, atual=None):
    def valor(campo):
        return dados[campo] if campo in dados else (getattr(atual, campo) if atual else None)

    data_visita = validar_data(valor("data_visita"), "data_visita", "a data da visita", obrigatorio=False)
    if data_visita and data_visita > hoje():
        raise ErroDeValidacao("A data da visita não pode estar no futuro.", campo="data_visita")
    return {
        "nota": validar_inteiro(valor("nota"), "nota", "a nota", minimo=1, maximo=5),
        "titulo": validar_texto(valor("titulo"), "titulo", "o título", maximo=120, obrigatorio=False),
        "comentario": validar_texto(valor("comentario"), "comentario", "o comentário", minimo=10, maximo=2000),
        "data_visita": data_visita,
    }


def _verificar_experiencia(avaliacao, repositorio):
    viagem = repositorio.viagem_concluida_com_lugar(avaliacao.usuario_id, avaliacao.lugar_id, hoje())
    avaliacao.experiencia_verificada = viagem is not None
    avaliacao.viagem_id = viagem.id if viagem else None


def _salvar_fotos(avaliacao, arquivos_enviados):
    arquivos_enviados = [a for a in (arquivos_enviados or []) if getattr(a, "filename", "")]
    if len(avaliacao.fotos) + len(arquivos_enviados) > Config.UPLOAD_MAXIMO_FOTOS:
        raise ErroDeValidacao(f"Cada avaliação pode ter até {Config.UPLOAD_MAXIMO_FOTOS} fotos.", campo="fotos")
    salvos = []
    try:
        for arquivo in arquivos_enviados:
            salvos.append(arquivos.salvar_imagem(arquivo, "avaliacoes"))
    except Exception:
        for nome in salvos:  # não deixa arquivos órfãos se uma das fotos for inválida
            arquivos.remover_imagem("avaliacoes", nome)
        raise
    for nome in salvos:
        avaliacao.fotos.append(FotoAvaliacao(arquivo=nome))
    return len(salvos)


def _avaliacao_propria(avaliacao_id, usuario):
    avaliacao = Avaliacao.buscar_por_id(avaliacao_id)
    if avaliacao is None or avaliacao.usuario_id != usuario.id:
        raise NaoEncontrado("Avaliação não encontrada.")
    return avaliacao


class ListarAvaliacoesLugarService:
    def executar(self, lugar_id, usuario=None, ordenar="recentes"):
        lugar = _lugar(lugar_id)
        consulta = (
            db.session.query(Avaliacao)
            .options(selectinload(Avaliacao.fotos), selectinload(Avaliacao.usuario))
            .filter(Avaliacao.lugar_id == lugar.id)
        )
        ordens = {
            "recentes": (Avaliacao.criado_em.desc(),),
            "melhores": (Avaliacao.nota.desc(), Avaliacao.criado_em.desc()),
            "piores": (Avaliacao.nota.asc(), Avaliacao.criado_em.desc()),
            "verificadas": (Avaliacao.experiencia_verificada.desc(), Avaliacao.criado_em.desc()),
        }
        avaliacoes = consulta.order_by(*ordens.get(ordenar, ordens["recentes"])).limit(100).all()
        notas = db.session.query(Avaliacao.nota, func.count(Avaliacao.id)).filter(
            Avaliacao.lugar_id == lugar.id).group_by(Avaliacao.nota).all()
        distribuicao = {n: 0 for n in range(1, 6)}
        distribuicao.update({int(n): int(t) for n, t in notas})
        total = sum(distribuicao.values())
        media = round(sum(n * t for n, t in distribuicao.items()) / total, 1) if total else None
        experiencias = (
            db.session.query(RegistroDiario)
            .filter(RegistroDiario.lugar_id == lugar.id, RegistroDiario.visibilidade == "publico")
            .order_by(RegistroDiario.data.desc()).limit(10).all()
        )
        minha = next((a for a in avaliacoes if usuario and a.usuario_id == usuario.id), None)
        if usuario and minha is None:
            minha = Avaliacao.buscar(usuario.id, lugar.id)
        return {
            "lugar_id": lugar.id,
            "comunidade": {"media": media, "total": total, "distribuicao": distribuicao,
                           "verificadas": sum(1 for a in avaliacoes if a.experiencia_verificada)},
            "catalogo": {"nota": round(lugar.nota, 1), "avaliacoes": lugar.avaliacoes},
            "avaliacoes": [a.to_dict(usuario.id if usuario else None) for a in avaliacoes],
            "minha": minha.to_dict(usuario.id) if minha else None,
            "experiencias": [e.to_dict() for e in experiencias],
        }


class CriarAvaliacaoService:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or ViagemRepository()

    def executar(self, lugar_id, usuario, dados, fotos=None):
        lugar = _lugar(lugar_id)
        if Avaliacao.buscar(usuario.id, lugar.id):
            raise ConflitoDeDados("Você já avaliou este lugar. Edite a sua avaliação.", campo="nota")
        avaliacao = Avaliacao(usuario_id=usuario.id, lugar_id=lugar.id, **_validar(dados))
        _verificar_experiencia(avaliacao, self.repositorio)
        _salvar_fotos(avaliacao, fotos)
        avaliacao.salvar()
        return {"mensagem": "Obrigado por compartilhar sua experiência!", "avaliacao": avaliacao.to_dict(usuario.id)}


class EditarAvaliacaoService:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or ViagemRepository()

    def executar(self, avaliacao_id, usuario, dados, fotos=None):
        avaliacao = _avaliacao_propria(avaliacao_id, usuario)
        for chave, valor in _validar(dados, atual=avaliacao).items():
            setattr(avaliacao, chave, valor)
        _verificar_experiencia(avaliacao, self.repositorio)
        _salvar_fotos(avaliacao, fotos)
        db.session.commit()
        return {"mensagem": "Avaliação atualizada.", "avaliacao": avaliacao.to_dict(usuario.id)}


class ExcluirAvaliacaoService:
    def executar(self, avaliacao_id, usuario):
        avaliacao = _avaliacao_propria(avaliacao_id, usuario)
        nomes = [f.arquivo for f in avaliacao.fotos]
        avaliacao.deletar()
        for nome in nomes:
            arquivos.remover_imagem("avaliacoes", nome)
        return {"mensagem": "Avaliação excluída.", "avaliacao_id": avaliacao_id}


class RemoverFotoAvaliacaoService:
    def executar(self, avaliacao_id, foto_id, usuario):
        avaliacao = _avaliacao_propria(avaliacao_id, usuario)
        foto = next((f for f in avaliacao.fotos if f.id == foto_id), None)
        if foto is None:
            raise NaoEncontrado("Foto não encontrada.")
        nome = foto.arquivo
        avaliacao.fotos.remove(foto)
        db.session.delete(foto)
        db.session.commit()
        arquivos.remover_imagem("avaliacoes", nome)
        return {"mensagem": "Foto removida.", "avaliacao": avaliacao.to_dict(usuario.id)}


class ListarComunidadeService:
    """Feed da comunidade: avaliações recentes e relatos públicos do diário."""

    def executar(self, usuario=None, limite=30):
        avaliacoes = (
            db.session.query(Avaliacao)
            .options(selectinload(Avaliacao.fotos), selectinload(Avaliacao.usuario), selectinload(Avaliacao.lugar))
            .order_by(Avaliacao.criado_em.desc()).limit(limite).all()
        )
        relatos = (
            db.session.query(RegistroDiario)
            .options(selectinload(RegistroDiario.fotos))
            .filter(RegistroDiario.visibilidade == "publico")
            .order_by(RegistroDiario.criado_em.desc()).limit(limite).all()
        )
        uid = usuario.id if usuario else None
        itens = [{"tipo": "avaliacao", "criado_em": a.criado_em.isoformat(), "avaliacao": a.to_dict(uid, com_lugar=True)}
                 for a in avaliacoes]
        itens += [{"tipo": "relato", "criado_em": r.criado_em.isoformat(), "relato": r.to_dict(uid)} for r in relatos]
        itens.sort(key=lambda i: i["criado_em"], reverse=True)
        return {"itens": itens[:limite]}
