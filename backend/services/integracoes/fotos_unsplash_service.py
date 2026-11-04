"""Integração externa: busca de fotos no Unsplash (requer UNSPLASH_ACCESS_KEY no .env).

Regras da API do Unsplash respeitadas: exibir a foto pelas URLs fornecidas (hotlink),
creditar o fotógrafo com links contendo utm_source, e registrar o "download" quando
a foto passa a ser usada (feito na aprovação da curadoria). Assim como no Pexels,
as fotos entram como candidatas NÃO verificadas.
"""
from backend.config import Config
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.erros import IntegracaoIndisponivel

URL_API = "https://api.unsplash.com"
UTM = "utm_source=viajai&utm_medium=referral"


class FotosUnsplashService:
    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    @property
    def configurado(self):
        return bool(self.config.UNSPLASH_ACCESS_KEY)

    def _cabecalhos(self):
        return {"Authorization": f"Client-ID {self.config.UNSPLASH_ACCESS_KEY}", "Accept-Version": "v1"}

    def executar(self, lugar, referencia=None, limite=5):
        if not self.configurado:
            raise IntegracaoIndisponivel("Configure UNSPLASH_ACCESS_KEY no .env para buscar no Unsplash.")
        consulta = (referencia or {}).get("consulta") or f"{lugar.nome} {lugar.cidade}"
        dados = self.cliente.requisitar_json(
            f"{URL_API}/search/photos", params={"query": consulta, "per_page": limite, "orientation": "landscape"},
            cabecalhos=self._cabecalhos(), cache_horas=24,
        )
        return [
            {
                "fonte": "unsplash",
                "id_externo": foto["id"],
                "url": foto["urls"]["regular"],
                "url_media": foto["urls"]["regular"],
                "url_miniatura": foto["urls"]["small"],
                "largura": foto.get("width"),
                "altura": foto.get("height"),
                "titulo": (foto.get("alt_description") or consulta)[:300],
                "autor": (foto.get("user") or {}).get("name"),
                "autor_url": f'{(foto.get("user") or {}).get("links", {}).get("html", "https://unsplash.com")}?{UTM}',
                "licenca": "Licença Unsplash",
                "licenca_url": "https://unsplash.com/license",
                "pagina_origem": f'{foto.get("links", {}).get("html", "https://unsplash.com")}?{UTM}',
                "verificada": False,
                "principal": False,
                "criterio": f"Busca por texto no Unsplash ('{consulta}') — requer conferência manual",
            }
            for foto in dados.get("results", [])
        ]

    def registrar_uso(self, id_externo):
        """Endpoint de download exigido pelas diretrizes da API ao usar uma foto."""
        if not self.configurado:
            return False
        try:
            self.cliente.requisitar_json(f"{URL_API}/photos/{id_externo}/download", cabecalhos=self._cabecalhos())
            return True
        except IntegracaoIndisponivel:
            return False
