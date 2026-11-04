"""Casos de uso do Planejamento Financeiro (feature 3).

    ResumoFinanceiroService · DefinirOrcamentoService · RegistrarDespesaService
    EditarDespesaService · ExcluirDespesaService
"""
from backend.extensions import db
from backend.models.despesa import CATEGORIAS_DESPESA, Despesa, PlanejamentoOrcamento
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.utils.erros import ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import (
    validar_data,
    validar_escolha,
    validar_inteiro,
    validar_texto,
    validar_valor_monetario,
)

LIMITE_ALERTA = 0.8  # avisa quando 80% do orçamento foi usado


def _reais(centavos):
    return round((centavos or 0) / 100, 2)


class ResumoFinanceiroService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        return self.montar(viagem, usuario)

    @staticmethod
    def montar(viagem, usuario=None):
        despesas = sorted(viagem.despesas, key=lambda d: (d.data or viagem.data_ida, d.id), reverse=True)
        gasto = sum(d.valor_centavos for d in despesas)
        orcamento = viagem.orcamento_centavos
        planejado = {p.categoria: p.valor_centavos for p in viagem.planejamento}
        categorias = []
        for chave, info in CATEGORIAS_DESPESA.items():
            total = sum(d.valor_centavos for d in despesas if d.categoria == chave)
            plano = planejado.get(chave)
            categorias.append({
                "categoria": chave, **info, "gasto": _reais(total),
                "planejado": _reais(plano) if plano is not None else None,
                "percentual_gasto": round(total * 100 / gasto, 1) if gasto else 0,
                "estourado": plano is not None and total > plano,
            })

        alertas = []
        if orcamento:
            uso = gasto / orcamento
            if uso > 1:
                alertas.append({"nivel": "erro", "texto": f"Orçamento ultrapassado em R$ {_reais(gasto - orcamento):,.2f}."})
            elif uso >= LIMITE_ALERTA:
                alertas.append({"nivel": "aviso", "texto": f"Atenção: {round(uso * 100)}% do orçamento já foi usado."})
        for item in categorias:
            if item["estourado"]:
                alertas.append({"nivel": "aviso", "texto": f"{item['rotulo']} passou do valor planejado."})

        pessoas = max(1, viagem.viajantes)
        por_pagador = {}
        for despesa in despesas:
            if despesa.pago_por:
                chave = despesa.pago_por.nome
                por_pagador[chave] = por_pagador.get(chave, 0) + despesa.valor_centavos
        return {
            "moeda": "BRL",
            "orcamento": _reais(orcamento) if orcamento is not None else None,
            "gasto": _reais(gasto),
            "saldo": _reais(orcamento - gasto) if orcamento is not None else None,
            "percentual_usado": round(gasto * 100 / orcamento, 1) if orcamento else None,
            "viajantes": pessoas,
            "orcamento_por_pessoa": _reais(orcamento / pessoas) if orcamento else None,
            "gasto_por_pessoa": _reais(gasto / pessoas),
            "gasto_por_dia": _reais(gasto / viagem.duracao_dias),
            "categorias": categorias,
            "por_pagador": [{"nome": k, "valor": _reais(v)} for k, v in sorted(por_pagador.items(), key=lambda x: -x[1])],
            "alertas": alertas,
            "despesas": [d.to_dict() for d in despesas],
            "pode_editar": AutorizacaoViagemService.pode(viagem, usuario, "edicao") if usuario else False,
            "membros": [{"id": viagem.proprietario_id, "nome": viagem.proprietario.nome}] + [
                {"id": p.usuario_id, "nome": p.usuario.nome} for p in viagem.participantes if p.status == "aceito"],
        }


class DefinirOrcamentoService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        if "orcamento" in dados:
            viagem.orcamento_centavos = validar_valor_monetario(dados.get("orcamento"), "orcamento", "o orçamento",
                                                                obrigatorio=False)
        planejamento = dados.get("planejamento") or {}
        if not isinstance(planejamento, dict):
            raise ErroDeValidacao("Planejamento por categoria inválido.", campo="planejamento")
        existentes = {p.categoria: p for p in viagem.planejamento}
        for categoria, valor in planejamento.items():
            if categoria not in CATEGORIAS_DESPESA:
                raise ErroDeValidacao("Categoria inválida.", campo="planejamento")
            centavos = validar_valor_monetario(valor, "planejamento", "o valor planejado", obrigatorio=False)
            if centavos is None:
                if categoria in existentes:
                    db.session.delete(existentes[categoria])
                continue
            item = existentes.get(categoria) or PlanejamentoOrcamento(viagem_id=viagem.id, categoria=categoria)
            item.valor_centavos = centavos
            db.session.add(item)
        db.session.commit()
        db.session.refresh(viagem)
        return {"mensagem": "Orçamento atualizado.", "financas": ResumoFinanceiroService.montar(viagem, usuario)}


def _validar_despesa(dados, viagem, atual=None):
    def valor(campo):
        return dados[campo] if campo in dados else (getattr(atual, campo) if atual else None)

    pago_por_id = dados.get("pago_por_id") if "pago_por_id" in dados else (atual.pago_por_id if atual else None)
    if pago_por_id not in (None, ""):
        pago_por_id = validar_inteiro(pago_por_id, "pago_por_id", "quem pagou", minimo=1)
        if pago_por_id not in viagem.membros_ids():
            raise ErroDeValidacao("Quem pagou precisa participar da viagem.", campo="pago_por_id")
    else:
        pago_por_id = None
    centavos = validar_valor_monetario(
        dados.get("valor") if "valor" in dados else (atual.valor_centavos / 100 if atual else None), "valor", "o valor")
    if centavos == 0:
        raise ErroDeValidacao("O valor precisa ser maior que zero.", campo="valor")
    data = validar_data(valor("data"), "data", "a data", obrigatorio=False)
    return {
        "descricao": validar_texto(valor("descricao"), "descricao", "a descrição", minimo=2, maximo=160),
        "categoria": validar_escolha(valor("categoria"), CATEGORIAS_DESPESA, "categoria", "categoria", padrao="outros"),
        "valor_centavos": centavos,
        "data": data,
        "pago_por_id": pago_por_id,
    }


def _despesa_autorizada(despesa_id, usuario, autorizacao):
    despesa = Despesa.buscar_por_id(despesa_id)
    if despesa is None:
        raise NaoEncontrado("Despesa não encontrada.")
    autorizacao.executar(despesa.viagem_id, usuario, "edicao")
    return despesa


class RegistrarDespesaService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        despesa = Despesa(viagem_id=viagem.id, criado_por_id=usuario.id, **_validar_despesa(dados, viagem))
        despesa.salvar()
        db.session.refresh(viagem)
        return {"mensagem": "Despesa registrada.", "despesa": despesa.to_dict(),
                "financas": ResumoFinanceiroService.montar(viagem, usuario)}


class EditarDespesaService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, despesa_id, usuario, dados):
        despesa = _despesa_autorizada(despesa_id, usuario, self.autorizacao)
        for chave, valor in _validar_despesa(dados, despesa.viagem, atual=despesa).items():
            setattr(despesa, chave, valor)
        db.session.commit()
        return {"mensagem": "Despesa atualizada.", "despesa": despesa.to_dict(),
                "financas": ResumoFinanceiroService.montar(despesa.viagem, usuario)}


class ExcluirDespesaService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, despesa_id, usuario):
        despesa = _despesa_autorizada(despesa_id, usuario, self.autorizacao)
        viagem = despesa.viagem
        viagem.despesas.remove(despesa)
        db.session.delete(despesa)
        db.session.commit()
        return {"mensagem": "Despesa excluída.", "financas": ResumoFinanceiroService.montar(viagem, usuario)}
