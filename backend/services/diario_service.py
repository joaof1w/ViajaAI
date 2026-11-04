"""Casos de uso do Histórico e Diário de Viagens (feature 10).

    ListarDiarioService · CriarRegistroDiarioService · EditarRegistroDiarioService
    ExcluirRegistroDiarioService · RemoverFotoDiarioService · EstatisticasViagemService
    ListarDiarioDaViagemService
"""
from collections import Counter

from sqlalchemy.orm import selectinload

from backend.config import Config
from backend.extensions import db
from backend.models.diario import VISIBILIDADES, FotoDiario, RegistroDiario
from backend.models.lugar import Lugar
from backend.repositories.viagem_repository import ViagemRepository
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.utils import arquivos
from backend.utils.datas import hoje
from backend.utils.erros import ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import validar_data, validar_escolha, validar_inteiro, validar_texto


def _validar(dados, usuario, autorizacao, atual=None):
    def valor(campo):
        return dados[campo] if campo in dados else (getattr(atual, campo) if atual else None)

    viagem = None
    viagem_id = valor("viagem_id")
    if viagem_id not in (None, "", 0, "0"):
        viagem = autorizacao.executar(validar_inteiro(viagem_id, "viagem_id", "a viagem", minimo=1), usuario, "leitura")
    lugar = None
    lugar_id = valor("lugar_id")
    if lugar_id not in (None, "", 0, "0"):
        lugar = Lugar.buscar_por_id(validar_inteiro(lugar_id, "lugar_id", "o lugar", minimo=1))
        if lugar is None:
            raise ErroDeValidacao("Lugar não encontrado.", campo="lugar_id")
    data = validar_data(valor("data") or (viagem.data_ida.isoformat() if viagem else None), "data", "a data")
    if data > hoje():
        raise ErroDeValidacao("O diário registra experiências já vividas: a data não pode estar no futuro.", campo="data")
    visibilidade = validar_escolha(valor("visibilidade"), VISIBILIDADES, "visibilidade", "visibilidade", padrao="privado")
    if visibilidade == "participantes" and viagem is None:
        raise ErroDeValidacao("Para compartilhar com os participantes, vincule o registro a uma viagem.",
                              campo="visibilidade")
    return {
        "viagem_id": viagem.id if viagem else None, "lugar_id": lugar.id if lugar else None,
        "titulo": validar_texto(valor("titulo"), "titulo", "o título", minimo=2, maximo=140),
        "relato": validar_texto(valor("relato"), "relato", "o relato", maximo=8000, obrigatorio=False),
        "data": data,
        "local": validar_texto(valor("local") or (lugar.nome if lugar else None), "local", "o local", maximo=160,
                               obrigatorio=False),
        "cidade": validar_texto(valor("cidade") or (lugar.cidade if lugar else None), "cidade", "a cidade", maximo=80,
                                obrigatorio=False),
        "estado": validar_texto(valor("estado") or (lugar.estado if lugar else None), "estado", "o estado/país",
                                maximo=60, obrigatorio=False),
        "nota_pessoal": validar_inteiro(valor("nota_pessoal"), "nota_pessoal", "a nota", minimo=1, maximo=5,
                                        obrigatorio=False),
        "visibilidade": visibilidade,
    }


def _salvar_fotos(registro, enviados):
    enviados = [a for a in (enviados or []) if getattr(a, "filename", "")]
    if len(registro.fotos) + len(enviados) > Config.UPLOAD_MAXIMO_FOTOS:
        raise ErroDeValidacao(f"Cada registro pode ter até {Config.UPLOAD_MAXIMO_FOTOS} fotos.", campo="fotos")
    salvos = []
    try:
        for arquivo in enviados:
            salvos.append(arquivos.salvar_imagem(arquivo, "diario"))
    except Exception:
        for nome in salvos:
            arquivos.remover_imagem("diario", nome)
        raise
    for nome in salvos:
        registro.fotos.append(FotoDiario(arquivo=nome))


def _registro_proprio(registro_id, usuario):
    registro = RegistroDiario.buscar_por_id(registro_id)
    if registro is None or registro.usuario_id != usuario.id:
        raise NaoEncontrado("Registro não encontrado.")
    return registro


class ListarDiarioService:
    def executar(self, usuario):
        registros = (
            db.session.query(RegistroDiario)
            .options(selectinload(RegistroDiario.fotos))
            .filter(RegistroDiario.usuario_id == usuario.id)
            .order_by(RegistroDiario.data.desc(), RegistroDiario.id.desc()).all()
        )
        linha_do_tempo = {}
        for registro in registros:
            ano = str(registro.data.year)
            linha_do_tempo.setdefault(ano, []).append(registro.to_dict(usuario.id))
        return {
            "total": len(registros),
            "linha_do_tempo": [{"ano": ano, "registros": itens} for ano, itens in linha_do_tempo.items()],
            "visibilidades": [{"valor": k, "rotulo": v} for k, v in VISIBILIDADES.items()],
        }


class ListarDiarioDaViagemService:
    """Registros compartilhados com os participantes (e os próprios) de uma viagem."""

    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        registros = (
            db.session.query(RegistroDiario)
            .filter(RegistroDiario.viagem_id == viagem.id,
                    (RegistroDiario.usuario_id == usuario.id) | RegistroDiario.visibilidade.in_(("participantes", "publico")))
            .order_by(RegistroDiario.data.asc()).all()
        )
        return {"registros": [r.to_dict(usuario.id) for r in registros]}


class CriarRegistroDiarioService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, usuario, dados, fotos=None):
        registro = RegistroDiario(usuario_id=usuario.id, **_validar(dados, usuario, self.autorizacao))
        _salvar_fotos(registro, fotos)
        registro.salvar()
        return {"mensagem": "Memória registrada no seu diário.", "registro": registro.to_dict(usuario.id)}


class EditarRegistroDiarioService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, registro_id, usuario, dados, fotos=None):
        registro = _registro_proprio(registro_id, usuario)
        for chave, valor in _validar(dados, usuario, self.autorizacao, atual=registro).items():
            setattr(registro, chave, valor)
        _salvar_fotos(registro, fotos)
        db.session.commit()
        return {"mensagem": "Registro atualizado.", "registro": registro.to_dict(usuario.id)}


class ExcluirRegistroDiarioService:
    def executar(self, registro_id, usuario):
        registro = _registro_proprio(registro_id, usuario)
        nomes = [f.arquivo for f in registro.fotos]
        registro.deletar()
        for nome in nomes:
            arquivos.remover_imagem("diario", nome)
        return {"mensagem": "Registro excluído.", "registro_id": registro_id}


class RemoverFotoDiarioService:
    def executar(self, registro_id, foto_id, usuario):
        registro = _registro_proprio(registro_id, usuario)
        foto = next((f for f in registro.fotos if f.id == foto_id), None)
        if foto is None:
            raise NaoEncontrado("Foto não encontrada.")
        nome = foto.arquivo
        registro.fotos.remove(foto)
        db.session.delete(foto)
        db.session.commit()
        arquivos.remover_imagem("diario", nome)
        return {"mensagem": "Foto removida.", "registro": registro.to_dict(usuario.id)}


class EstatisticasViagemService:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or ViagemRepository()

    def executar(self, usuario):
        viagens = self.repositorio.listar_do_usuario(usuario.id)
        concluidas = [v for v in viagens if v.status == "concluida"]
        registros = db.session.query(RegistroDiario).filter(RegistroDiario.usuario_id == usuario.id).all()

        destinos, estados, lugares, categorias = set(), set(), set(), Counter()
        for viagem in concluidas:
            destinos.add(viagem.destino.strip().lower())
            if viagem.lugar:
                estados.add(viagem.lugar.estado)
                lugares.add(viagem.lugar.id)
                categorias[viagem.lugar.categoria] += 1
        for registro in registros:
            if registro.cidade:
                destinos.add(registro.cidade.strip().lower())
            if registro.estado:
                estados.add(registro.estado.strip().upper())
            if registro.lugar:
                lugares.add(registro.lugar.id)
                categorias[registro.lugar.categoria] += 1
        notas = [r.nota_pessoal for r in registros if r.nota_pessoal]
        return {
            "viagens_concluidas": len(concluidas),
            "viagens_planejadas": sum(1 for v in viagens if v.status != "concluida"),
            "dias_viajados": sum(v.duracao_dias for v in concluidas),
            "destinos_conhecidos": len(destinos),
            "estados_visitados": sorted(estados),
            "lugares_do_catalogo": len(lugares),
            "registros": len(registros),
            "fotos": sum(len(r.fotos) for r in registros),
            "nota_media_pessoal": round(sum(notas) / len(notas), 1) if notas else None,
            "categoria_favorita": categorias.most_common(1)[0][0] if categorias else None,
            "viagens": [
                {"id": v.id, "titulo": v.titulo, "destino": v.destino, "data_ida": v.data_ida.isoformat(),
                 "data_volta": v.data_volta.isoformat(), "duracao_dias": v.duracao_dias}
                for v in sorted(concluidas, key=lambda v: v.data_ida, reverse=True)
            ],
        }
