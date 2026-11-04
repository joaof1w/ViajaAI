"""Casos de uso do Checklist Inteligente (feature 6).

    ListarChecklistService · GerarSugestoesChecklistService · AdicionarItemChecklistService
    AtualizarItemChecklistService · RemoverItemChecklistService · ImportarChecklistService
"""
import re
import unicodedata

from backend.extensions import db
from backend.models.checklist import CATEGORIAS_CHECKLIST, ItemChecklist
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.utils.erros import ErroDeNegocio, ErroDeValidacao, NaoEncontrado
from backend.utils.validadores import validar_booleano, validar_escolha, validar_inteiro, validar_texto

MAXIMO_ITENS = 300

BASE = [
    ("documentos", "Documento de identidade com foto (RG ou CNH)"),
    ("documentos", "Cartões de pagamento e um pouco de dinheiro"),
    ("documentos", "Comprovantes de reservas (hospedagem e transporte)"),
    ("documentos", "Cartão do plano de saúde"),
    ("eletronicos", "Celular e carregador"),
    ("eletronicos", "Carregador portátil (power bank)"),
    ("higiene", "Escova e pasta de dente"),
    ("higiene", "Desodorante"),
    ("higiene", "Itens de higiene pessoal"),
    ("saude", "Medicamentos de uso contínuo"),
    ("saude", "Kit básico de primeiros socorros"),
    ("roupas", "Roupas íntimas e meias"),
    ("roupas", "Pijama"),
    ("outros", "Garrafa de água reutilizável"),
]

POR_INTERESSE = {
    "praia": [("roupas", "Roupas de banho"), ("higiene", "Protetor solar"), ("outros", "Óculos de sol"),
              ("roupas", "Chinelo"), ("outros", "Canga ou toalha de praia"), ("roupas", "Chapéu ou boné")],
    "natureza": [("roupas", "Tênis ou bota para trilha"), ("saude", "Repelente de insetos"),
                 ("higiene", "Protetor solar"), ("outros", "Mochila pequena para passeios"),
                 ("roupas", "Capa de chuva leve")],
    "aventura": [("roupas", "Tênis ou bota para trilha"), ("saude", "Repelente de insetos"),
                 ("roupas", "Roupas de secagem rápida"), ("outros", "Lanterna"), ("roupas", "Roupas de banho")],
    "cultura": [("roupas", "Calçado confortável para caminhar"), ("outros", "Mochila pequena para passeios")],
    "museus": [("roupas", "Calçado confortável para caminhar"), ("eletronicos", "Fones de ouvido para audioguias")],
    "gastronomia": [("documentos", "Reservas dos restaurantes"), ("roupas", "Uma roupa mais arrumada para jantar")],
}

POR_TIPO = {
    "negocios": [("eletronicos", "Notebook e carregador"), ("roupas", "Roupa social"), ("documentos", "Documentos de trabalho")],
    "familia": [("saude", "Remédios e itens das crianças"), ("outros", "Lanches para o caminho"),
                ("documentos", "Documentos dos menores e autorização de viagem, se necessário")],
    "mochilao": [("outros", "Cadeado para mala/armário"), ("outros", "Toalha de secagem rápida"),
                 ("eletronicos", "Adaptador de tomada universal")],
    "romantica": [("roupas", "Roupa para uma ocasião especial")],
    "aventura": [("saude", "Seguro viagem com cobertura para esportes")],
}


def _chave(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if c.isalnum())


def sugerir_itens(viagem, interesses):
    dias = viagem.duracao_dias
    itens = list(BASE)
    itens.append(("roupas", f"Roupas para {dias} {'dia' if dias == 1 else 'dias'} (inclua uma muda extra)"))
    if dias >= 4:
        itens.append(("higiene", "Sabão ou saquinhos para roupa suja"))
    if viagem.viajantes > 1:
        itens.append(("outros", "Combinar com o grupo quem leva itens compartilhados"))
    categorias = set(interesses or [])
    if viagem.lugar is not None:
        categorias.add(viagem.lugar.categoria)
    for categoria in categorias:
        itens.extend(POR_INTERESSE.get(categoria, []))
    itens.extend(POR_TIPO.get(viagem.tipo, []))
    # Sem país confirmado, não supomos viagem internacional — apenas lembramos de conferir.
    nacional = viagem.lugar is not None or "brasil" in _chave(viagem.destino) or \
        re.search(r",\s*[A-Z]{2}$", viagem.destino.strip())
    if not nacional:
        itens.append(("documentos", "Conferir se o destino exige passaporte, visto ou vacinas"))
    vistos, unicos = set(), []
    for categoria, texto in itens:
        if _chave(texto) not in vistos:
            vistos.add(_chave(texto))
            unicos.append((categoria, texto))
    return unicos


def _resposta(viagem, usuario):
    itens = sorted(viagem.itens_checklist, key=lambda i: (list(CATEGORIAS_CHECKLIST).index(i.categoria)
                                                          if i.categoria in CATEGORIAS_CHECKLIST else 99, i.ordem, i.id))
    concluidos = sum(1 for i in itens if i.concluido)
    return {
        "itens": [i.to_dict() for i in itens],
        "total": len(itens),
        "concluidos": concluidos,
        "percentual": round(concluidos * 100 / len(itens)) if itens else 0,
        "categorias": [{"valor": k, **v} for k, v in CATEGORIAS_CHECKLIST.items()],
        "pode_editar": AutorizacaoViagemService.pode(viagem, usuario, "edicao"),
    }


def _item_autorizado(item_id, usuario, autorizacao):
    item = ItemChecklist.buscar_por_id(item_id)
    if item is None:
        raise NaoEncontrado("Item não encontrado.")
    autorizacao.executar(item.viagem_id, usuario, "edicao")
    return item


class ListarChecklistService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        return _resposta(self.autorizacao.executar(viagem_id, usuario, "leitura"), usuario)


class GerarSugestoesChecklistService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        interesses = usuario.preferencia.slugs_interesses if usuario.preferencia else []
        existentes = {_chave(i.texto) for i in viagem.itens_checklist}
        novos = 0
        for ordem, (categoria, texto) in enumerate(sugerir_itens(viagem, interesses)):
            if _chave(texto) in existentes or len(viagem.itens_checklist) >= MAXIMO_ITENS:
                continue
            viagem.itens_checklist.append(ItemChecklist(categoria=categoria, texto=texto, sugerido=True, ordem=ordem,
                                                        atualizado_por_id=usuario.id))
            novos += 1
        db.session.commit()
        resposta = _resposta(viagem, usuario)
        resposta["mensagem"] = f"{novos} sugestões adicionadas." if novos else "Sua lista já tem todas as sugestões."
        return resposta


class AdicionarItemChecklistService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        viagem = self.autorizacao.executar(viagem_id, usuario, "edicao")
        if len(viagem.itens_checklist) >= MAXIMO_ITENS:
            raise ErroDeNegocio("Sua lista atingiu o limite de itens.")
        texto = validar_texto(dados.get("texto"), "texto", "o item", maximo=160)
        if _chave(texto) in {_chave(i.texto) for i in viagem.itens_checklist}:
            raise ErroDeValidacao("Este item já está na lista.", campo="texto")
        item = ItemChecklist(
            viagem_id=viagem.id, texto=texto, atualizado_por_id=usuario.id,
            categoria=validar_escolha(dados.get("categoria"), CATEGORIAS_CHECKLIST, "categoria", "categoria", padrao="outros"),
            ordem=max((i.ordem for i in viagem.itens_checklist), default=0) + 1,
        )
        item.salvar()
        db.session.refresh(viagem)
        return {"mensagem": "Item adicionado.", "item": item.to_dict(), **_resposta(viagem, usuario)}


class AtualizarItemChecklistService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, item_id, usuario, dados):
        item = _item_autorizado(item_id, usuario, self.autorizacao)
        if "concluido" in dados:
            item.concluido = validar_booleano(dados["concluido"])
        if "texto" in dados:
            item.texto = validar_texto(dados["texto"], "texto", "o item", maximo=160)
        if "categoria" in dados:
            item.categoria = validar_escolha(dados["categoria"], CATEGORIAS_CHECKLIST, "categoria", "categoria")
        if "ordem" in dados:
            item.ordem = validar_inteiro(dados["ordem"], "ordem", "a ordem", minimo=0, maximo=10_000)
        item.atualizado_por_id = usuario.id
        db.session.commit()
        return {"item": item.to_dict(), **_resposta(item.viagem, usuario)}


class RemoverItemChecklistService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, item_id, usuario):
        item = _item_autorizado(item_id, usuario, self.autorizacao)
        viagem = item.viagem
        viagem.itens_checklist.remove(item)
        db.session.delete(item)
        db.session.commit()
        return {"mensagem": "Item removido.", **_resposta(viagem, usuario)}


class ImportarChecklistService:
    """Reaproveita a lista de outra viagem à qual o usuário tem acesso (itens desmarcados)."""

    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario, dados):
        destino = self.autorizacao.executar(viagem_id, usuario, "edicao")
        origem_id = validar_inteiro(dados.get("origem_viagem_id"), "origem_viagem_id", "a viagem de origem", minimo=1)
        if origem_id == destino.id:
            raise ErroDeValidacao("Escolha outra viagem como origem.", campo="origem_viagem_id")
        origem = self.autorizacao.executar(origem_id, usuario, "leitura")
        existentes = {_chave(i.texto) for i in destino.itens_checklist}
        copiados = 0
        for item in sorted(origem.itens_checklist, key=lambda i: (i.ordem, i.id)):
            if _chave(item.texto) in existentes or len(destino.itens_checklist) >= MAXIMO_ITENS:
                continue
            destino.itens_checklist.append(ItemChecklist(categoria=item.categoria, texto=item.texto, ordem=item.ordem,
                                                         sugerido=item.sugerido, atualizado_por_id=usuario.id))
            existentes.add(_chave(item.texto))
            copiados += 1
        db.session.commit()
        return {"mensagem": f"{copiados} itens importados de '{origem.titulo}'.", **_resposta(destino, usuario)}
