"""Validações reutilizadas pelos Services (nunca pelas Controllers)."""
import re

from backend.config import Config
from backend.utils.erros import ErroDeValidacao

REGEX_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


def validar_nome(nome):
    nome = (nome or "").strip()
    if len(nome) < 3:
        raise ErroDeValidacao("Informe seu nome completo (mínimo 3 caracteres).", campo="nome")
    if not re.match(r"^[A-Za-zÀ-ÿ'\s.-]+$", nome):
        raise ErroDeValidacao("O nome deve conter apenas letras.", campo="nome")
    return nome


def validar_email(email):
    """Valida o formato do e-mail. Levanta ErroDeValidacao quando inválido."""
    email = (email or "").strip().lower()
    if not email:
        raise ErroDeValidacao("Informe um e-mail.", campo="email")
    if len(email) > 120 or not REGEX_EMAIL.match(email):
        raise ErroDeValidacao("E-mail inválido. Use o formato nome@dominio.com.", campo="email")
    if ".." in email:
        raise ErroDeValidacao("E-mail inválido.", campo="email")
    return email


def validar_senha(senha, confirmacao=None):
    """Senha com no mínimo SENHA_TAMANHO_MINIMO (6) caracteres."""
    senha = senha or ""
    minimo = Config.SENHA_TAMANHO_MINIMO
    if len(senha) < minimo:
        raise ErroDeValidacao(
            f"A senha deve ter no mínimo {minimo} caracteres.", campo="senha"
        )
    if senha.strip() == "":
        raise ErroDeValidacao("A senha não pode conter apenas espaços.", campo="senha")
    if confirmacao is not None and senha != confirmacao:
        raise ErroDeValidacao("As senhas não conferem.", campo="confirmacao_senha")
    return senha


def validar_codigo(codigo):
    codigo = re.sub(r"\D", "", codigo or "")
    if len(codigo) != 6:
        raise ErroDeValidacao("O código deve ter 6 dígitos.", campo="codigo")
    return codigo


def validar_orcamento(orcamento):
    try:
        orcamento = int(orcamento)
    except (TypeError, ValueError):
        raise ErroDeValidacao("Orçamento inválido.", campo="orcamento")
    if orcamento not in (1, 2, 3, 4):
        raise ErroDeValidacao("O orçamento deve estar entre 1 e 4.", campo="orcamento")
    return orcamento
