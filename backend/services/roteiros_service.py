"""Casos de uso dos Roteiros (feature 2): versões, geração pelo Vai e edição de atividades.

    GerarRoteiroService · ListarRoteirosService · CriarRoteiroManualService
    DuplicarRoteiroService · AtivarRoteiroService · ExcluirRoteiroService
    AdicionarAtividadeService · EditarAtividadeService · ExcluirAtividadeService
    ReorganizarAtividadesService
"""
import json

from backend.extensions import db
from backend.models.lugar import Lugar
from backend.models.ponto_interesse import PontoInteresse
from backend.models.roteiro import CATEGORIAS_ATIVIDADE, AtividadeRoteiro, Roteiro
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.services.roteiro_inteligente_service import RITMOS, RoteiroInteligenteService
from backend.utils.erros import ErroDeNegocio, ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import (
    validar_booleano,
    validar_coordenadas,
    validar_escolha,
    validar_hora,
    validar_inteiro,
    validar_orcamento,
    validar_texto,
)

MAXIMO_VERSOES = 20
MAXIMO_ATIVIDADES = 300


def nova_versao_roteiro(viagem, usuario, titulo, origem, parametros=None, observacoes=None):
    if len(viagem.roteiros) >= MAXIMO_VERSOES:
        raise ErroDeNegocio(f"Limite de {MAXIMO_VERSOES} versões de roteiro. Exclua versões antigas.")
    for roteiro in viagem.roteiros:
        roteiro.ativo = False
    roteiro = Roteiro(
        viagem_id=viagem.id, versao=Roteiro.proxima_versao(viagem.id), titulo=titulo, origem=origem,
        ativo=True, parametros=json.dumps(parametros or {}, ensure_ascii=False), observacoes_ia=observacoes,
        criado_por_id=usuario.id,
    )
    viagem.roteiros.append(roteiro)
    return roteiro


def _roteiro_autorizado(roteiro_id, usuario, autorizacao, nivel):
    roteiro = Roteiro.buscar_por_id(roteiro_id)
    if roteiro is None:
        raise NaoEncontrado("Roteiro não encontrado.")
    autorizacao.executar(roteiro.viagem_id, usuario, nivel)
    return roteiro


def _atividade_autorizada(atividade_id, usuario, autorizacao):
    atividade = AtividadeRoteiro.buscar_por_id(atividade_id)
    if atividade is None:
        raise NaoEncontrado("Atividade não encontrada.")
    autorizacao.executar(atividade.roteiro.viagem_id, usuario, "edicao")
    return atividade


def validar_atividade(dados, viagem, atual=None):
    def valor(campo, padrao=None):
        if campo in dados:
            return dados[campo]
        return getattr(atual, campo) if atual is not None else padrao

    campos = {
        "titulo": validar_texto(valor("titulo"), "titulo", "o título da atividade", minimo=2, maximo=160),
        "descricao": validar_texto(valor("descricao"), "descricao", "a descrição", maximo=1500, obrigatorio=False),
        "dia": validar_inteiro(valor("dia", 1), "dia", "o dia", minimo=1, maximo=viagem.duracao_dias),
        "categoria": validar_escolha(valor("categoria"), CATEGORIAS_ATIVIDADE, "categoria", "categoria", padrao="atracao"),
        "horario": validar_hora(valor("horario"), "horario", "o horário"),
        "duracao_min": validar_inteiro(valor("duracao_min"), "duracao_min", "a duração (min)", minimo=5,
                                       maximo=24 * 60, obrigatorio=False),
        "endereco": validar_texto(valor("endereco"), "endereco", "o endereço", maximo=200, obrigatorio=False),
    }
    lugar_id = valor("lugar_id")
    lugar = Lugar.buscar_por_id(validar_inteiro(lugar_id, "lugar_id", "lugar", minimo=1)) if lugar_id else None
    if lugar_id and lugar is None:
        raise ErroDeValidacao("Lugar do catálogo não encontrado.", campo="lugar_id")
    ponto_id = valor("ponto_id")
    ponto = PontoInteresse.buscar_por_id(validar_inteiro(ponto_id, "ponto_id", "ponto", minimo=1)) if ponto_id else None
    if ponto_id and ponto is None:
        raise ErroDeValidacao("Ponto do mapa não encontrado.", campo="ponto_id")
    lat, lon = validar_coordenadas(valor("latitude"), valor("longitude"))
    if lat is None and lugar is not None:
        lat, lon = lugar.latitude, lugar.longitude
    if lat is None and ponto is not None:
        lat, lon = ponto.latitude, ponto.longitude
    campos.update(
        lugar_id=lugar.id if lugar else None, ponto_id=ponto.id if ponto else None, latitude=lat, longitude=lon,
        funcionamento=ponto.funcionamento if ponto else (atual.funcionamento if atual else None),
    )
    if "horario" in dados:  # horário digitado pelo usuário deixa de ser "sugerido"
        campos["horario_sugerido"] = False
    return campos


class GerarRoteiroService:
    def __init__(self, autorizacao=None, motor=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()
        self.motor = motor or RoteiroInteligenteService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        preferencia = usuario.preferencia
        interesses = dados.get("interesses")
        if not isinstance(interesses, list) or not interesses:
            interesses = preferencia.slugs_interesses if preferencia else []
        parametros = {
            "interesses": [str(i)[:40] for i in interesses][:10],
            "orcamento": validar_orcamento(dados.get("orcamento") or (preferencia.orcamento if preferencia else 2)),
            "ritmo": validar_escolha(dados.get("ritmo"), RITMOS, "ritmo", "ritmo", padrao="moderado"),
            "incluir_refeicoes": validar_booleano(dados.get("incluir_refeicoes", True)),
            "observacoes": validar_texto(dados.get("observacoes"), "observacoes", "as observações", maximo=500,
                                         obrigatorio=False),
        }
        resultado = self.motor.executar(viagem, parametros)
        roteiro = nova_versao_roteiro(
            viagem, usuario, f"Roteiro do Vai · versão {Roteiro.proxima_versao(viagem.id)}",
            resultado["origem"], parametros, resultado["observacoes"],
        )
        ordem_por_dia = {}
        for item in resultado["atividades"]:
            ordem_por_dia[item["dia"]] = ordem_por_dia.get(item["dia"], 0) + 1
            roteiro.atividades.append(AtividadeRoteiro(ordem=ordem_por_dia[item["dia"]], **{
                chave: item.get(chave) for chave in (
                    "dia", "titulo", "descricao", "categoria", "horario", "duracao_min", "lugar_id", "ponto_id",
                    "endereco", "latitude", "longitude", "funcionamento", "fonte")
            }, horario_sugerido=bool(item.get("horario_sugerido"))))
        db.session.commit()
        return {"mensagem": "Roteiro gerado pelo Vai!", "roteiro": roteiro.to_dict(),
                "total_candidatos": resultado["total_candidatos"]}


class ListarRoteirosService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        versoes = sorted(viagem.roteiros, key=lambda r: r.versao, reverse=True)
        ativo = viagem.roteiro_ativo
        return {
            "versoes": [r.to_dict(com_atividades=False) for r in versoes],
            "ativo": ativo.to_dict() if ativo else None,
            "categorias": [{"valor": k, "rotulo": v} for k, v in CATEGORIAS_ATIVIDADE.items()],
            "duracao_dias": viagem.duracao_dias,
            "data_ida": viagem.data_ida.isoformat(),
        }


class ObterRoteiroService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario):
        return _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "leitura").to_dict()


class CriarRoteiroManualService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        titulo = validar_texto(dados.get("titulo") or "Meu roteiro", "titulo", "o título", maximo=120)
        roteiro = nova_versao_roteiro(viagem, usuario, titulo, "manual")
        db.session.commit()
        return {"mensagem": "Roteiro criado.", "roteiro": roteiro.to_dict()}


class DuplicarRoteiroService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario):
        original = _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "edicao")
        copia = nova_versao_roteiro(original.viagem, usuario, f"{original.titulo} (cópia)"[:120], "copia",
                              json.loads(original.parametros or "{}"), original.observacoes_ia)
        for atividade in original.atividades:
            copia.atividades.append(AtividadeRoteiro(**{
                coluna: getattr(atividade, coluna) for coluna in (
                    "dia", "ordem", "titulo", "descricao", "categoria", "horario", "horario_sugerido", "duracao_min",
                    "lugar_id", "ponto_id", "endereco", "latitude", "longitude", "funcionamento", "fonte")
            }))
        db.session.commit()
        return {"mensagem": "Versão duplicada.", "roteiro": copia.to_dict()}


class AtivarRoteiroService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario):
        roteiro = _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "edicao")
        for outro in roteiro.viagem.roteiros:
            outro.ativo = outro.id == roteiro.id
        db.session.commit()
        return {"mensagem": f"Versão {roteiro.versao} definida como principal.", "roteiro": roteiro.to_dict()}


class ExcluirRoteiroService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario):
        roteiro = _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "edicao")
        era_ativo = roteiro.ativo
        outros = [r for r in roteiro.viagem.roteiros if r.id != roteiro.id]
        db.session.delete(roteiro)
        db.session.flush()
        if era_ativo and outros:  # a versão mais recente restante vira a principal
            max(outros, key=lambda r: r.versao).ativo = True
        db.session.commit()
        return {"mensagem": "Versão excluída.", "roteiro_id": roteiro_id}


class AdicionarAtividadeService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario, dados):
        roteiro = _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "edicao")
        if len(roteiro.atividades) >= MAXIMO_ATIVIDADES:
            raise ErroDeNegocio("Este roteiro já tem atividades demais.")
        campos = validar_atividade(dados, roteiro.viagem)
        campos.setdefault("horario_sugerido", False)
        ordem = max((a.ordem for a in roteiro.atividades if a.dia == campos["dia"]), default=0) + 1
        atividade = AtividadeRoteiro(roteiro_id=roteiro.id, ordem=ordem, fonte="manual", **campos)
        atividade.salvar()
        return {"mensagem": "Atividade adicionada.", "atividade": atividade.to_dict()}


class EditarAtividadeService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, atividade_id, usuario, dados):
        atividade = _atividade_autorizada(atividade_id, usuario, self.autorizacao)
        campos = validar_atividade(dados, atividade.roteiro.viagem, atual=atividade)
        if campos["dia"] != atividade.dia:
            campos["ordem"] = max((a.ordem for a in atividade.roteiro.atividades if a.dia == campos["dia"]),
                                  default=0) + 1
        for chave, valor in campos.items():
            setattr(atividade, chave, valor)
        db.session.commit()
        return {"mensagem": "Atividade atualizada.", "atividade": atividade.to_dict()}


class ExcluirAtividadeService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, atividade_id, usuario):
        atividade = _atividade_autorizada(atividade_id, usuario, self.autorizacao)
        atividade.deletar()
        return {"mensagem": "Atividade removida.", "atividade_id": atividade_id}


class ReorganizarAtividadesService:
    """Recebe [{id, dia, ordem}] e aplica em lote (mover entre dias e reordenar)."""

    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, roteiro_id, usuario, dados):
        roteiro = _roteiro_autorizado(roteiro_id, usuario, self.autorizacao, "edicao")
        itens = dados.get("itens")
        if not isinstance(itens, list) or not itens:
            raise ErroDeValidacao("Envie a nova ordem das atividades.", campo="itens")
        por_id = {a.id: a for a in roteiro.atividades}
        for item in itens:
            if not isinstance(item, dict):
                raise ErroDeValidacao("Formato inválido.", campo="itens")
            atividade = por_id.get(validar_inteiro(item.get("id"), "itens", "atividade", minimo=1))
            if atividade is None:
                raise ErroDeValidacao("Atividade não pertence a este roteiro.", campo="itens")
            atividade.dia = validar_inteiro(item.get("dia"), "itens", "o dia", minimo=1,
                                            maximo=roteiro.viagem.duracao_dias)
            atividade.ordem = validar_inteiro(item.get("ordem"), "itens", "a ordem", minimo=0, maximo=10_000)
        db.session.commit()
        db.session.refresh(roteiro)
        return {"mensagem": "Roteiro reorganizado.", "roteiro": roteiro.to_dict()}
