"""Integração externa: busca de fotos no Pexels (requer PEXELS_API_KEY no .env).

Buscas por texto NÃO garantem que a foto seja do lugar — por isso tudo que vem do
Pexels entra como candidata NÃO verificada e só aparece depois da curadoria
(tools/fotos.py aprovar <id>). Atribuição exigida: fotógrafo + link para o Pexels.
"""
from backend.config import Config
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.erros import IntegracaoIndisponivel

URL_BUSCA = "https://api.pexels.com/v1/search"


class FotosPexelsService:
    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    @property
    def configurado(self):
        return bool(self.config.PEXELS_API_KEY)

    def executar(self, lugar, referencia=None, limite=5):
        if not self.configurado:
            raise IntegracaoIndisponivel("Configure PEXELS_API_KEY no .env para buscar no Pexels.")
        consulta = (referencia or {}).get("consulta") or f"{lugar.nome} {lugar.cidade}"
        dados = self.cliente.requisitar_json(
            URL_BUSCA, params={"query": consulta, "per_page": limite, "locale": "pt-BR"},
            cabecalhos={"Authorization": self.config.PEXELS_API_KEY}, cache_horas=24,
        )
        return [
            {
                "fonte": "pexels",
                "id_externo": str(foto["id"]),
                "url": foto["src"].get("large2x") or foto["src"]["original"],
                "url_media": foto["src"].get("large"),
                "url_miniatura": foto["src"].get("medium"),
                "url_original": foto["src"].get("original"),
                "largura": foto.get("width"),
                "altura": foto.get("height"),
                "titulo": (foto.get("alt") or consulta)[:300],
                "autor": foto.get("photographer"),
                "autor_url": foto.get("photographer_url"),
                "licenca": "Licença Pexels",
                "licenca_url": "https://www.pexels.com/license/",
                "pagina_origem": foto.get("url"),
                "verificada": False,
                "principal": False,
                "criterio": f"Busca por texto no Pexels ('{consulta}') — requer conferência manual",
            }
            for foto in dados.get("photos", [])
        ]
