"""Extração do usuário autenticado a partir do cabeçalho Authorization."""
from functools import wraps

from flask import g, request

from backend.models.usuario import Usuario
from backend.utils.erros import NaoAutorizado


def usuario_do_token():
    cabecalho = request.headers.get("Authorization", "")
    token = cabecalho[7:].strip() if cabecalho.lower().startswith("bearer ") else ""
    if not token:
        token = request.headers.get("X-Token", "").strip()
    if not token:
        return None
    return Usuario.buscar_por_token(token)


def login_obrigatorio(funcao):
    """Decorator usado nas Controllers para rotas protegidas."""

    @wraps(funcao)
    def envolucro(*args, **kwargs):
        usuario = usuario_do_token()
        if usuario is None:
            raise NaoAutorizado("Sessão expirada. Faça login novamente.")
        g.usuario = usuario
        return funcao(*args, **kwargs)

    return envolucro
