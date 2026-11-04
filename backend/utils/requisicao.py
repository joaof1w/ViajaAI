"""Leitura uniforme do corpo da requisição (JSON ou multipart com fotos)."""
from flask import request


def dados_e_fotos():
    """Devolve (dados, fotos). Em multipart, os campos vêm do formulário e as fotos de 'fotos'."""
    if request.mimetype == "multipart/form-data":
        dados = {chave: valor for chave, valor in request.form.items()}
        return dados, request.files.getlist("fotos")
    return request.get_json(silent=True) or {}, []


def corpo_json():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}
