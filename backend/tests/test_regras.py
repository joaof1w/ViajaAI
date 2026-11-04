"""Testes das regras de negócio que não dependem do banco.

Execute na raiz do projeto:  python -m backend.tests.test_regras
"""
import sys
import types

from backend.services.assistente_local_service import AssistenteLocalService
from backend.services.calcular_match_service import CalcularMatchService
from backend.utils.erros import ErroDeValidacao
from backend.utils.geo import coordenadas_da_cidade, distancia_km
from backend.utils.validadores import (
    validar_codigo,
    validar_email,
    validar_nome,
    validar_orcamento,
    validar_senha,
)

falhas = []


def checar(condicao, descricao):
    if condicao:
        print(f"  ok   {descricao}")
    else:
        falhas.append(descricao)
        print(f"  FALHA {descricao}")


def levanta(funcao, *args):
    try:
        funcao(*args)
        return False
    except ErroDeValidacao:
        return True


def testar_validacoes():
    print("\nValidações")
    checar(validar_email(" Ana.Lima@Email.com ") == "ana.lima@email.com", "e-mail normalizado")
    for invalido in ["", "ana", "ana@", "ana@email", "ana@@email.com", "a..b@email.com", "ana email@x.com"]:
        checar(levanta(validar_email, invalido), f"e-mail inválido recusado: {invalido!r}")
    checar(validar_senha("123456") == "123456", "senha de 6 caracteres aceita")
    for curta in ["", "1", "12345", "     "]:
        checar(levanta(validar_senha, curta), f"senha inválida recusada: {curta!r}")
    checar(levanta(validar_senha, "123456", "654321"), "confirmação divergente recusada")
    checar(validar_nome(" Ana Lima ") == "Ana Lima", "nome aparado")
    checar(levanta(validar_nome, "A1"), "nome com número recusado")
    checar(validar_codigo("12 34-56") == "123456", "código limpo")
    checar(levanta(validar_codigo, "123"), "código curto recusado")
    checar(validar_orcamento("3") == 3, "orçamento convertido")
    checar(levanta(validar_orcamento, 9), "orçamento fora da faixa recusado")


def testar_distancias():
    print("\nDistâncias")
    sp = coordenadas_da_cidade("São Paulo", "SP")
    rio = coordenadas_da_cidade("Rio de Janeiro", "RJ")
    d = distancia_km(sp, rio)
    checar(330 < d < 375, f"São Paulo → Rio ≈ {d} km (esperado ~360)")
    checar(distancia_km(sp, sp) == 0.0, "mesma cidade = 0 km")
    checar(coordenadas_da_cidade("Cidade Inexistente", "ZZ") == sp, "cidade desconhecida usa o padrão")


def _lugar(categoria, nota, preco, popularidade=0):
    return types.SimpleNamespace(
        categoria=categoria, nota=nota, faixa_preco=preco, popularidade=popularidade,
        latitude=-23.55, longitude=-46.63,
    )


def _preferencia(interesses, orcamento):
    return types.SimpleNamespace(
        slugs_interesses=interesses, orcamento=orcamento, cidade="São Paulo", estado="SP"
    )


def testar_match():
    print("\nCálculo de match")
    servico = CalcularMatchService()
    perfil = _preferencia(["praia", "gastronomia"], 2)

    alinhado = servico.executar(_lugar("praia", 4.9, 2), perfil, distancia=10)
    fora = servico.executar(_lugar("museus", 4.9, 4), perfil, distancia=2000)
    checar(alinhado > fora, f"lugar alinhado ({alinhado}%) pontua mais que o fora do perfil ({fora}%)")
    checar(35 <= alinhado <= 99 and 35 <= fora <= 99, "match sempre entre 35% e 99%")

    perto = servico.executar(_lugar("praia", 4.5, 2), perfil, distancia=20)
    longe = servico.executar(_lugar("praia", 4.5, 2), perfil, distancia=3000)
    checar(perto > longe, f"proximidade aumenta o match ({perto}% > {longe}%)")

    popular = servico.executar(_lugar("praia", 4.2, 2, popularidade=5), perfil, distancia=3000)
    base = servico.executar(_lugar("praia", 4.2, 2), perfil, distancia=3000)
    checar(popular > base, f"popularidade aumenta o match ({popular}% > {base}%)")
    checar(servico.executar(_lugar("praia", 4.9, 2), None, distancia=0) > 0, "funciona sem preferências")


def testar_assistente_local():
    print("\nAssistente local (fallback da IA)")
    servico = AssistenteLocalService()
    contexto = {
        "nome": "Ana", "cidade": "São Paulo", "orcamento_rotulo": "Moderado",
        "interesses": ["Praia"],
        "lugares": [{
            "nome": "Praia do Espelho", "local": "Trancoso, BA", "nota": 4.9, "preco_simbolo": "$$",
            "match": 97, "categoria": "praia", "descricao": "Falésias e piscinas naturais.",
            "melhor_epoca": "Setembro a março", "distancia_km": 1240,
        }],
    }
    checar("Dia 1" in servico.executar("me sugere um roteiro", contexto), "responde a pedido de roteiro")
    checar("Setembro" in servico.executar("qual a melhor época?", contexto), "responde sobre melhor época")
    checar("Moderado" in servico.executar("quanto custa?", contexto), "responde sobre preços")
    checar("Praia do Espelho" in servico.executar("qualquer outra pergunta", contexto), "resposta padrão cita lugares")
    checar(bool(servico.executar("oi", {})), "não quebra sem contexto")


if __name__ == "__main__":
    testar_validacoes()
    testar_distancias()
    testar_match()
    testar_assistente_local()
    print("\n" + ("TODOS OS TESTES PASSARAM ✓" if not falhas else f"{len(falhas)} FALHA(S): {falhas}"))
    sys.exit(1 if falhas else 0)
