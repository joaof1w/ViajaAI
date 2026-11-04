"""Infraestrutura comum dos testes de integração (app isolado, usuários e arquivos)."""
import io
import os
import shutil
import tempfile
import unittest

from backend.config import Config

_PASTA_TEMP = tempfile.mkdtemp(prefix="viajai-testes-")
Config.PASTA_UPLOADS = os.path.join(_PASTA_TEMP, "uploads")  # uploads isolados dos reais


def criar_config(banco):
    class ConfigTeste(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{banco}"
        INTEGRACOES_EXTERNAS = False
        FOTOS_SINCRONIZACAO_AUTOMATICA = False
        LIMITE_REQUISICOES_ATIVO = False
        GEMINI_API_KEY = ""

    return ConfigTeste


def imagem_png(largura=40, altura=30, cor=(255, 107, 53)):
    from PIL import Image

    saida = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(saida, "PNG")
    saida.seek(0)
    return saida


class CasoComApp(unittest.TestCase):
    """Cria um banco SQLite novo por classe de teste."""

    @classmethod
    def setUpClass(cls):
        from backend.app import create_app
        from backend.utils.limite_requisicoes import limpar_limites

        Config.INTEGRACOES_EXTERNAS = False
        limpar_limites()
        cls.pasta = tempfile.mkdtemp(dir=_PASTA_TEMP)
        cls.app = create_app(criar_config(os.path.join(cls.pasta, "teste.db")))
        cls.cliente = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        from backend.extensions import db

        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        shutil.rmtree(cls.pasta, ignore_errors=True)

    # ------------------------------------------------------------------
    def requisitar(self, metodo, caminho, token=None, json=None, **kwargs):
        cabecalhos = kwargs.pop("headers", {})
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        resposta = self.cliente.open(caminho, method=metodo, json=json, headers=cabecalhos, **kwargs)
        return resposta.status_code, (resposta.get_json(silent=True) or {})

    _contador = 0

    def criar_usuario(self, nome="Ana Lima", email=None, senha="segredo1", preferencias=True,
                      interesses=("praia", "gastronomia"), cidade="São Paulo", estado="SP"):
        if email is None:  # e-mail único por chamada (as classes compartilham o banco)
            CasoComApp._contador += 1
            email = f"pessoa{CasoComApp._contador}@email.com"
        status, dados = self.requisitar("POST", "/api/auth/cadastro", json={
            "nome": nome, "email": email, "senha": senha, "confirmacao_senha": senha})
        self.assertEqual(status, 201, dados)
        status, dados = self.requisitar("POST", "/api/auth/verificar", json={
            "email": email, "codigo": dados["codigo_debug"]})
        self.assertEqual(status, 200, dados)
        token = dados["token"]
        if preferencias:
            status, _ = self.requisitar("PUT", "/api/preferencias", token, json={
                "interesses": list(interesses), "orcamento": 2, "cidade": cidade, "estado": estado})
            self.assertEqual(status, 200)
        return token, dados["usuario"]["id"]

    def lugar_por_nome(self, nome):
        with self.app.app_context():
            from backend.models.lugar import Lugar

            return Lugar.query.filter_by(nome=nome).first().id
