"""Integração externa: geocodificação de destinos digitados livremente (Nominatim/OSM).

Política de uso do Nominatim: no máximo 1 requisição por segundo, User-Agent
identificado e cache dos resultados — tudo garantido pelo ClienteHttp.
"""
from backend.config import Config
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.erros import IntegracaoIndisponivel


class GeocodificacaoService:
    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    def executar(self, consulta):
        """Devolve {latitude, longitude, nome, pais_codigo} ou None se não achar/indisponível."""
        consulta = (consulta or "").strip()
        if len(consulta) < 2:
            return None
        try:
            resultados = self.cliente.requisitar_json(
                self.config.NOMINATIM_URL,
                params={"q": consulta, "format": "jsonv2", "limit": 1, "addressdetails": 1,
                        "accept-language": "pt-BR"},
                cache_horas=24 * 30,
            )
        except IntegracaoIndisponivel:
            return None
        if not resultados:
            return None
        primeiro = resultados[0]
        try:
            return {
                "latitude": round(float(primeiro["lat"]), 6),
                "longitude": round(float(primeiro["lon"]), 6),
                "nome": primeiro.get("display_name"),
                "pais_codigo": (primeiro.get("address") or {}).get("country_code", "").upper() or None,
            }
        except (KeyError, TypeError, ValueError):
            return None
