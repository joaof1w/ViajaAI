"""Cliente HTTP compartilhado pelas integrações externas.

- Identifica a aplicação com User-Agent (exigência da Wikimedia e do Nominatim).
- Respeita um intervalo mínimo entre chamadas ao mesmo host (Nominatim: 1 req/s).
- Guarda respostas no CacheExterno para não repetir chamadas.
- Nunca deixa uma falha externa derrubar a requisição do usuário: lança
  IntegracaoIndisponivel, que os Services tratam com uma resposta alternativa.
"""
import hashlib
import json
import threading
import time
from urllib.parse import urlparse

import requests

from backend.config import Config
from backend.models.cache_externo import CacheExterno
from backend.utils.erros import IntegracaoIndisponivel

INTERVALO_MINIMO = {
    "nominatim.openstreetmap.org": 1.1,
    "overpass-api.de": 1.0,
    "commons.wikimedia.org": 0.2,
}

_ultima_chamada = {}
_trava = threading.Lock()


class ClienteHttp:
    def __init__(self, config=None, sessao=None):
        self.config = config or Config
        self.sessao = sessao or requests

    @property
    def habilitado(self):
        return bool(self.config.INTEGRACOES_EXTERNAS)

    def _aguardar_vez(self, url):
        host = urlparse(url).hostname or ""
        intervalo = next((v for k, v in INTERVALO_MINIMO.items() if host.endswith(k)), 0)
        if not intervalo:
            return
        with _trava:
            espera = _ultima_chamada.get(host, 0) + intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            _ultima_chamada[host] = time.monotonic()

    def requisitar_json(self, url, params=None, metodo="GET", dados=None, cabecalhos=None,
                        cache_horas=None, chave_cache=None):
        if not self.habilitado:
            raise IntegracaoIndisponivel("Integrações externas desativadas (INTEGRACOES_EXTERNAS=0).")

        chave = None
        if cache_horas:
            base = chave_cache or (url + json.dumps(params or {}, sort_keys=True) + json.dumps(dados or {}, sort_keys=True))
            chave = "http:" + hashlib.sha256(base.encode()).hexdigest()
            em_cache = CacheExterno.ler(chave)
            if em_cache is not None:
                return em_cache

        todos_cabecalhos = {"User-Agent": self.config.HTTP_USER_AGENT, "Accept": "application/json"}
        todos_cabecalhos.update(cabecalhos or {})
        self._aguardar_vez(url)
        try:
            if metodo == "POST":
                resposta = self.sessao.post(url, params=params, data=dados, headers=todos_cabecalhos,
                                            timeout=self.config.HTTP_TIMEOUT)
            else:
                resposta = self.sessao.get(url, params=params, headers=todos_cabecalhos,
                                           timeout=self.config.HTTP_TIMEOUT)
            if resposta.status_code == 429:
                raise IntegracaoIndisponivel("Limite de uso do serviço externo atingido. Tente mais tarde.")
            resposta.raise_for_status()
            conteudo = resposta.json()
        except IntegracaoIndisponivel:
            raise
        except Exception as erro:  # rede bloqueada, timeout, JSON inválido...
            print(f"[ClienteHttp] falha em {urlparse(url).hostname}: {erro}", flush=True)
            raise IntegracaoIndisponivel("Serviço externo indisponível no momento.")

        if chave:
            CacheExterno.gravar(chave, conteudo, cache_horas)
        return conteudo
