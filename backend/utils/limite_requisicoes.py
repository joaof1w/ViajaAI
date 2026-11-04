"""Limitação simples de requisições (janela deslizante em memória).

Protege rotas sensíveis — login, cadastro, convites, uploads, IA e integrações
externas — contra abuso e força bruta. Em produção com vários processos, troque o
armazenamento por um compartilhado (ex.: Redis); a interface continua a mesma.
"""
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, g, request

from backend.utils.erros import LimiteExcedido

_registros = defaultdict(deque)
_trava = threading.Lock()


def _identidade():
    usuario = getattr(g, "usuario", None)
    if usuario is not None:
        return f"u{usuario.id}"
    return f"ip{request.remote_addr or 'desconhecido'}"


def verificar_limite(chave, maximo, janela_segundos):
    if not current_app.config.get("LIMITE_REQUISICOES_ATIVO", True):
        return
    agora = time.monotonic()
    with _trava:
        fila = _registros[chave]
        while fila and agora - fila[0] > janela_segundos:
            fila.popleft()
        if len(fila) >= maximo:
            raise LimiteExcedido("Muitas tentativas em pouco tempo. Aguarde um instante e tente de novo.")
        fila.append(agora)


def limitar(nome, maximo, janela_segundos):
    """Decorator: no máximo `maximo` chamadas por usuário/IP a cada `janela_segundos`."""

    def decorador(funcao):
        @wraps(funcao)
        def envolucro(*args, **kwargs):
            verificar_limite(f"{nome}:{_identidade()}", maximo, janela_segundos)
            return funcao(*args, **kwargs)

        return envolucro

    return decorador


def limpar_limites():
    with _trava:
        _registros.clear()
