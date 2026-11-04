"""Casos de uso do Planejador de Viagens (feature 1).

    CriarViagemService · ListarViagensService · ObterViagemService
    EditarViagemService · ExcluirViagemService
"""
from backend.extensions import db
from backend.models.lugar import Lugar
from backend.models.viagem import TIPOS_VIAGEM, ParticipanteViagem, Viagem
from backend.repositories.viagem_repository import ViagemRepository
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.services.integracoes.geocodificacao_service import GeocodificacaoService
from backend.utils.erros import ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import (
    validar_coordenadas,
    validar_data,
    validar_escolha,
    validar_inteiro,
    validar_texto,
    validar_valor_monetario,
)

DURACAO_MAXIMA_DIAS = 90


def _validar_dados_viagem(dados, atual=None):
    """Valida e normaliza os campos; `atual` permite edição parcial."""
    def valor(campo):
        return dados[campo] if campo in dados else (getattr(atual, campo) if atual else None)

    lugar = None
    lugar_id = dados.get("lugar_id") if "lugar_id" in dados else (atual.lugar_id if atual else None)
    if lugar_id not in (None, "", 0):
        lugar = Lugar.buscar_por_id(validar_inteiro(lugar_id, "lugar_id", "destino do catálogo", minimo=1))
        if lugar is None:
            raise ErroDeValidacao("Destino do catálogo não encontrado.", campo="lugar_id")

    destino = validar_texto(valor("destino") or (f"{lugar.cidade}, {lugar.estado}" if lugar else None),
                            "destino", "o destino", minimo=2, maximo=160)
    titulo = validar_texto(valor("titulo") or (f"Viagem para {destino}"), "titulo", "o nome da viagem",
                           minimo=2, maximo=120)
    data_ida = validar_data(valor("data_ida"), "data_ida", "a data de partida")
    data_volta = validar_data(valor("data_volta"), "data_volta", "a data de retorno")
    if data_volta < data_ida:
        raise ErroDeValidacao("A data de retorno não pode ser antes da partida.", campo="data_volta")
    if (data_volta - data_ida).days + 1 > DURACAO_MAXIMA_DIAS:
        raise ErroDeValidacao(f"A viagem pode ter no máximo {DURACAO_MAXIMA_DIAS} dias.", campo="data_volta")
    viajantes = validar_inteiro(1 if valor("viajantes") is None else valor("viajantes"), "viajantes", "a quantidade de viajantes", minimo=1, maximo=50)
    tipo = validar_escolha(valor("tipo"), TIPOS_VIAGEM, "tipo", "tipo de viagem", padrao="lazer")
    orcamento = validar_valor_monetario(
        dados.get("orcamento") if "orcamento" in dados else (
            atual.orcamento_centavos / 100 if atual and atual.orcamento_centavos is not None else None),
        "orcamento", "o orçamento", obrigatorio=False)
    observacoes = validar_texto(valor("observacoes"), "observacoes", "as observações", maximo=2000, obrigatorio=False)
    preferencias = validar_texto(valor("preferencias"), "preferencias", "as preferências", maximo=1000, obrigatorio=False)
    return {
        "lugar": lugar, "destino": destino, "titulo": titulo, "data_ida": data_ida, "data_volta": data_volta,
        "viajantes": viajantes, "tipo": tipo, "orcamento_centavos": orcamento,
        "observacoes": observacoes, "preferencias": preferencias,
    }


def _definir_coordenadas(viagem, dados, geocodificador, destino_mudou):
    lat, lon = validar_coordenadas(dados.get("latitude"), dados.get("longitude"))
    if lat is not None:
        viagem.latitude, viagem.longitude = lat, lon
    elif viagem.lugar is not None:
        viagem.latitude, viagem.longitude = viagem.lugar.latitude, viagem.lugar.longitude
    elif destino_mudou:
        local = geocodificador.executar(viagem.destino)  # None se offline/sem resultado
        viagem.latitude = local["latitude"] if local else None
        viagem.longitude = local["longitude"] if local else None


class CriarViagemService:
    def __init__(self, geocodificador=None):
        self.geocodificador = geocodificador or GeocodificacaoService()

    def executar(self, usuario, dados):
        campos = _validar_dados_viagem(dados)
        lugar = campos.pop("lugar")
        viagem = Viagem(proprietario_id=usuario.id, lugar_id=lugar.id if lugar else None, **campos)
        viagem.lugar = lugar
        _definir_coordenadas(viagem, dados, self.geocodificador, destino_mudou=True)
        viagem.salvar()
        return {"mensagem": "Viagem criada!", "viagem": viagem.to_dict(usuario.id)}


class ListarViagensService:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or ViagemRepository()

    def executar(self, usuario, status=None):
        viagens = self.repositorio.listar_do_usuario(usuario.id)
        itens = [v.to_dict(usuario.id, resumo=True) for v in viagens]
        contagem = {"futura": 0, "em_andamento": 0, "concluida": 0}
        for item in itens:
            contagem[item["status"]] += 1
        if status in contagem:
            itens = [i for i in itens if i["status"] == status]
        # Em andamento e futuras: as mais próximas primeiro; concluídas: as mais recentes primeiro.
        abertas = sorted((i for i in itens if i["status"] != "concluida"),
                         key=lambda i: (i["status"] != "em_andamento", i["data_ida"]))
        concluidas = sorted((i for i in itens if i["status"] == "concluida"),
                            key=lambda i: i["data_volta"], reverse=True)
        itens = abertas + concluidas
        return {
            "total": len(itens),
            "contagem": contagem,
            "convites_pendentes": len(ParticipanteViagem.convites_pendentes(usuario.id)),
            "viagens": itens,
            "tipos": [{"valor": k, "rotulo": v} for k, v in TIPOS_VIAGEM.items()],
        }


class ObterViagemService:
    def __init__(self, autorizacao=None, repositorio=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()
        self.repositorio = repositorio or ViagemRepository()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        dados = viagem.to_dict(usuario.id)
        dados["resumo"] = self.repositorio.resumo(viagem)
        dados["permissoes"] = {
            "editar": AutorizacaoViagemService.pode(viagem, usuario, "edicao"),
            "gerenciar": AutorizacaoViagemService.pode(viagem, usuario, "proprietario"),
        }
        return dados


class EditarViagemService:
    def __init__(self, autorizacao=None, geocodificador=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()
        self.geocodificador = geocodificador or GeocodificacaoService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "proprietario")
        destino_anterior, lugar_anterior = viagem.destino, viagem.lugar_id
        campos = _validar_dados_viagem(dados, atual=viagem)
        lugar = campos.pop("lugar")
        for chave, valor in campos.items():
            setattr(viagem, chave, valor)
        viagem.lugar_id = lugar.id if lugar else None
        viagem.lugar = lugar
        mudou = viagem.destino != destino_anterior or viagem.lugar_id != lugar_anterior
        _definir_coordenadas(viagem, dados, self.geocodificador, destino_mudou=mudou)
        db.session.commit()
        return {"mensagem": "Viagem atualizada.", "viagem": viagem.to_dict(usuario.id)}


class ExcluirViagemService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "proprietario")
        titulo = viagem.titulo
        viagem.deletar()  # cascata: roteiros, gastos, agenda, checklist, sugestões e participantes
        return {"mensagem": f"A viagem '{titulo}' foi excluída.", "viagem_id": viagem_id}


__all__ = ["CriarViagemService", "ListarViagensService", "ObterViagemService", "EditarViagemService",
           "ExcluirViagemService", "NaoEncontrado"]
