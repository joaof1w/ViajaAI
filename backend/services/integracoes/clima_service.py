"""Integração externa: previsão do tempo para os próximos dias (Open-Meteo, sem chave).

Quando o serviço não responde, devolve None — a interface mostra apenas a
"melhor época" do catálogo, sem inventar dados climáticos.
"""
from backend.config import Config
from backend.services.integracoes.cliente_http import ClienteHttp
from backend.utils.erros import IntegracaoIndisponivel


class ClimaService:
    def __init__(self, cliente=None, config=None):
        self.config = config or Config
        self.cliente = cliente or ClienteHttp(self.config)

    def executar(self, latitude, longitude):
        try:
            dados = self.cliente.requisitar_json(
                self.config.OPEN_METEO_URL,
                params={
                    "latitude": round(latitude, 3),
                    "longitude": round(longitude, 3),
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 7,
                },
                cache_horas=6,
            )
            diario = dados["daily"]
            maximas = [v for v in diario["temperature_2m_max"] if v is not None]
            minimas = [v for v in diario["temperature_2m_min"] if v is not None]
            chuva = [v for v in diario.get("precipitation_probability_max", []) if v is not None]
            if not maximas or not minimas:
                return None
            return {
                "fonte": "Open-Meteo",
                "fonte_url": "https://open-meteo.com",
                "periodo": "próximos 7 dias",
                "maxima_media": round(sum(maximas) / len(maximas), 1),
                "minima_media": round(sum(minimas) / len(minimas), 1),
                "chuva_probabilidade_media": round(sum(chuva) / len(chuva)) if chuva else None,
                "dias": [
                    {"data": d, "maxima": mx, "minima": mn}
                    for d, mx, mn in zip(diario["time"], diario["temperature_2m_max"], diario["temperature_2m_min"])
                ],
            }
        except (IntegracaoIndisponivel, KeyError, TypeError, ValueError, ZeroDivisionError):
            return None
