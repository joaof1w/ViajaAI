"""Integração externa: fotografias reais de cada lugar (Wikipédia + Wikimedia Commons).

Não exige chave. Critérios para considerar uma foto VERIFICADA (representa o lugar):

1. Imagem principal do artigo da Wikipédia sobre o lugar, desde que as coordenadas
   do artigo fiquem a até `raio_km` das coordenadas do lugar no catálogo; ou
2. Foto georreferenciada do Commons tirada a até `raio_km` do lugar E com o nome do
   lugar (ou um termo de referência curado) no título do arquivo.

Somente licenças livres (CC0, CC BY, CC BY-SA, domínio público) são aceitas, e
autor, licença e página de origem são armazenados para a atribuição obrigatória.
"""
import html
import re
import unicodedata

from backend.config import Config
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.erros import IntegracaoIndisponivel
from backend.utils.geo import distancia_km

LICENCAS_LIVRES = re.compile(r"^(cc0|cc[ -]by|public domain|pd|domínio público|attribution)", re.I)
PALAVRAS_GENERICAS = {
    "praia", "de", "do", "da", "dos", "das", "e", "restaurante", "centro", "historico", "trilha",
    "flutuacao", "no", "na", "instituto", "museu", "a", "o", "canion", "chapada", "mercado",
    "municipal", "sao", "rio", "teatro", "baia",
}
LARGURA_MEDIA = 1280
LARGURA_MINIATURA = 480
LARGURA_AMPLIADA = 1920


def normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    texto = re.sub(r"[̀-ͯ]", "", texto)
    return re.sub(r"[^a-z0-9 ]+", " ", texto)


def termos_do_lugar(nome, extras=None):
    termos = [p for p in normalizar(nome).split() if p not in PALAVRAS_GENERICAS and len(p) > 2]
    return list(dict.fromkeys([normalizar(t).strip() for t in (extras or [])] + termos))


def limpar_html(valor):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", valor or ""))).strip()


def miniatura(url_thumb, largura):
    """Wikimedia gera miniaturas sob demanda trocando o prefixo 'NNNpx-' da URL."""
    if not url_thumb:
        return None
    return re.sub(r"/(\d+)px-", f"/{largura}px-", url_thumb, count=1)


class FotosWikimediaService:
    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    # ------------------------------------------------------------------
    def executar(self, lugar, referencia=None, limite=5):
        """Lista de candidatas (dicts) para o lugar. Lança IntegracaoIndisponivel se offline."""
        referencia = referencia or {}
        raio = float(referencia.get("raio_km", 15))
        termos = termos_do_lugar(lugar.nome, referencia.get("palavras"))
        candidatas = []

        arquivo, artigo = self._imagem_do_artigo(lugar, referencia, raio)
        if arquivo:
            for info in self._informacoes([arquivo]):
                info.update(verificada=True, principal=True,
                            criterio=f"Imagem principal do artigo '{artigo}' da Wikipédia "
                                     f"(coordenadas a até {raio:g} km do lugar)")
                candidatas.append(info)

        restantes = max(0, limite - len(candidatas))
        if restantes:
            titulos = self._fotos_georreferenciadas(lugar, termos, raio, restantes + 4)
            ja = {c["id_externo"] for c in candidatas}
            for info in self._informacoes([t for t in titulos if t not in ja]):
                info.update(verificada=True, principal=False,
                            criterio=f"Foto georreferenciada a até {raio:g} km do lugar, com o nome dele no título")
                candidatas.append(info)
                if len(candidatas) >= limite:
                    break
        return candidatas

    # ------------------------------------------------------------------
    def _imagem_do_artigo(self, lugar, referencia, raio):
        for idioma in ("pt", "en"):
            titulo = (referencia.get("wikipedia") or {}).get(idioma)
            variantes = ([{"titles": titulo}] if titulo else []) + [
                {"generator": "search", "gsrsearch": f"{lugar.nome} {lugar.cidade}", "gsrlimit": 3}
            ]
            for variante in variantes:
                params = {
                    "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
                    "prop": "pageimages|coordinates", "piprop": "name", "colimit": 1, **variante,
                }
                dados = self.cliente.requisitar_json(
                    self.config.WIKIPEDIA_API_URL.format(idioma=idioma), params=params, cache_horas=24 * 7
                )
                for pagina in (dados.get("query") or {}).get("pages", []):
                    coordenadas = (pagina.get("coordinates") or [None])[0]
                    imagem = pagina.get("pageimage")
                    if not coordenadas or not imagem:
                        continue
                    distancia = distancia_km(
                        (lugar.latitude, lugar.longitude), (coordenadas["lat"], coordenadas["lon"])
                    )
                    # A coordenada do artigo precisa bater com a do lugar: evita homônimos.
                    if distancia <= raio:
                        return f"File:{imagem}", f"{idioma}:{pagina.get('title')}"
        return None, None

    def _fotos_georreferenciadas(self, lugar, termos, raio, limite):
        if not termos:
            return []
        dados = self.cliente.requisitar_json(
            self.config.COMMONS_API_URL,
            params={
                "action": "query", "format": "json", "formatversion": 2, "list": "geosearch",
                "gsnamespace": 6, "gscoord": f"{lugar.latitude}|{lugar.longitude}",
                "gsradius": int(min(10000, raio * 1000)), "gslimit": 100,
            },
            cache_horas=24 * 7,
        )
        titulos = []
        for item in (dados.get("query") or {}).get("geosearch", []):
            titulo = item.get("title", "")
            if not re.search(r"\.(jpe?g)$", titulo, re.I):
                continue
            if any(termo in normalizar(titulo) for termo in termos):
                titulos.append(titulo)
            if len(titulos) >= limite:
                break
        return titulos

    def _informacoes(self, titulos):
        if not titulos:
            return []
        dados = self.cliente.requisitar_json(
            self.config.COMMONS_API_URL,
            params={
                "action": "query", "format": "json", "formatversion": 2, "titles": "|".join(titulos[:20]),
                "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": LARGURA_MEDIA,
            },
            cache_horas=24 * 7,
        )
        resultado = []
        for pagina in (dados.get("query") or {}).get("pages", []):
            info = (pagina.get("imageinfo") or [None])[0]
            if not info or pagina.get("missing"):
                continue
            meta = info.get("extmetadata") or {}
            licenca = limpar_html((meta.get("LicenseShortName") or {}).get("value"))
            if meta.get("NonFree", {}).get("value") in ("true", True) or not LICENCAS_LIVRES.match(licenca or ""):
                continue
            if info.get("mime") not in ("image/jpeg", "image/png", "image/webp") or (info.get("width") or 0) < 800:
                continue
            media = info.get("thumburl") or info.get("url")
            resultado.append({
                "fonte": "wikimedia",
                "id_externo": pagina.get("title"),
                # Ampliada (lightbox): 1920 px, ou o original quando ele for menor.
                "url": (miniatura(info.get("thumburl"), LARGURA_AMPLIADA)
                        if (info.get("width") or 0) > LARGURA_AMPLIADA else info.get("url")),
                "url_media": media,
                "url_miniatura": miniatura(info.get("thumburl"), LARGURA_MINIATURA) or media,
                "largura": info.get("width"),
                "altura": info.get("height"),
                "titulo": limpar_html((meta.get("ObjectName") or {}).get("value")) or pagina.get("title"),
                "autor": (limpar_html((meta.get("Artist") or {}).get("value")) or "Autor desconhecido")[:200],
                "licenca": licenca[:80],
                "licenca_url": (meta.get("LicenseUrl") or {}).get("value"),
                "pagina_origem": info.get("descriptionurl"),
                "url_original": info.get("url"),
            })
        return resultado


__all__ = ["FotosWikimediaService", "IntegracaoIndisponivel", "termos_do_lugar", "miniatura"]
