"""Controller do Mapa Interativo (Leaflet + OpenStreetMap)."""
from flask import Blueprint, g, jsonify, request

from backend.services.mapa_service import (
    ConfiguracaoMapaService,
    LugaresNoMapaService,
    MapaViagemService,
    ProximidadesLugarService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar


class MapaController:
    def __init__(self):
        self.configuracao_mapa_service = ConfiguracaoMapaService()
        self.lugares_no_mapa_service = LugaresNoMapaService()
        self.mapa_viagem_service = MapaViagemService()
        self.proximidades_lugar_service = ProximidadesLugarService()

    def configuracao(self):
        return jsonify(self.configuracao_mapa_service.executar()), 200

    def lugares(self):
        return jsonify(self.lugares_no_mapa_service.executar()), 200

    def viagem(self, viagem_id):
        return jsonify(self.mapa_viagem_service.executar(viagem_id, g.usuario)), 200

    def proximidades(self, lugar_id):
        tipos = [t for t in (request.args.get("tipos") or "").split(",") if t] or None
        raio = request.args.get("raio_km", 5, type=float)
        return jsonify(self.proximidades_lugar_service.executar(lugar_id, raio, tipos)), 200

    def registrar(self, app):
        bp = Blueprint("mapa", __name__, url_prefix="/api")
        bp.add_url_rule("/mapa/config", view_func=self.configuracao, methods=["GET"])
        bp.add_url_rule("/mapa/lugares", view_func=self.lugares, methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/mapa", view_func=login_obrigatorio(self.viagem), methods=["GET"])
        bp.add_url_rule("/lugares/<int:lugar_id>/proximidades",
                        view_func=limitar("proximidades", 30, 60)(self.proximidades), methods=["GET"])
        app.register_blueprint(bp)
        return bp
