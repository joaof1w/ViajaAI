"""Controller dos recursos ParticipanteViagem e SugestaoViagem (viagens em grupo)."""
from flask import Blueprint, g, jsonify

from backend.services.grupo_service import (
    AlterarPapelService,
    ConvidarParticipanteService,
    CriarSugestaoService,
    DecidirSugestaoService,
    ListarConvitesService,
    ListarParticipantesService,
    ListarSugestoesService,
    RemoverParticipanteService,
    ResponderConviteService,
    VotarSugestaoService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar
from backend.utils.requisicao import corpo_json


class GrupoController:
    def __init__(self):
        self.listar_participantes_service = ListarParticipantesService()
        self.convidar_participante_service = ConvidarParticipanteService()
        self.alterar_papel_service = AlterarPapelService()
        self.remover_participante_service = RemoverParticipanteService()
        self.listar_convites_service = ListarConvitesService()
        self.responder_convite_service = ResponderConviteService()
        self.listar_sugestoes_service = ListarSugestoesService()
        self.criar_sugestao_service = CriarSugestaoService()
        self.votar_sugestao_service = VotarSugestaoService()
        self.decidir_sugestao_service = DecidirSugestaoService()

    def participantes(self, viagem_id):
        return jsonify(self.listar_participantes_service.executar(viagem_id, g.usuario)), 200

    def convidar(self, viagem_id):
        return jsonify(self.convidar_participante_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def alterar_papel(self, viagem_id, participante_id):
        return jsonify(self.alterar_papel_service.executar(viagem_id, participante_id, g.usuario, corpo_json())), 200

    def remover(self, viagem_id, participante_id):
        return jsonify(self.remover_participante_service.executar(viagem_id, participante_id, g.usuario)), 200

    def convites(self):
        return jsonify(self.listar_convites_service.executar(g.usuario)), 200

    def aceitar(self, convite_id):
        return jsonify(self.responder_convite_service.executar(convite_id, g.usuario, aceitar=True)), 200

    def recusar(self, convite_id):
        return jsonify(self.responder_convite_service.executar(convite_id, g.usuario, aceitar=False)), 200

    def sugestoes(self, viagem_id):
        return jsonify(self.listar_sugestoes_service.executar(viagem_id, g.usuario)), 200

    def sugerir(self, viagem_id):
        return jsonify(self.criar_sugestao_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def votar(self, sugestao_id):
        return jsonify(self.votar_sugestao_service.executar(sugestao_id, g.usuario, corpo_json())), 200

    def decidir(self, sugestao_id):
        return jsonify(self.decidir_sugestao_service.executar(sugestao_id, g.usuario, corpo_json())), 200

    def registrar(self, app):
        bp = Blueprint("grupo", __name__, url_prefix="/api")
        p = login_obrigatorio
        bp.add_url_rule("/viagens/<int:viagem_id>/participantes", view_func=p(self.participantes), methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/participantes",
                        view_func=p(limitar("convidar", 20, 600)(self.convidar)), methods=["POST"])
        bp.add_url_rule("/viagens/<int:viagem_id>/participantes/<int:participante_id>", view_func=p(self.alterar_papel),
                        methods=["PATCH", "PUT"])
        bp.add_url_rule("/viagens/<int:viagem_id>/participantes/<int:participante_id>", view_func=p(self.remover),
                        methods=["DELETE"])
        bp.add_url_rule("/convites", view_func=p(self.convites), methods=["GET"])
        bp.add_url_rule("/convites/<int:convite_id>/aceitar", view_func=p(self.aceitar), methods=["POST"])
        bp.add_url_rule("/convites/<int:convite_id>/recusar", view_func=p(self.recusar), methods=["POST"])
        bp.add_url_rule("/viagens/<int:viagem_id>/sugestoes", view_func=p(self.sugestoes), methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/sugestoes", view_func=p(limitar("sugerir", 30, 600)(self.sugerir)),
                        methods=["POST"])
        bp.add_url_rule("/sugestoes/<int:sugestao_id>/voto", view_func=p(self.votar), methods=["POST"])
        bp.add_url_rule("/sugestoes/<int:sugestao_id>/decisao", view_func=p(self.decidir), methods=["POST"])
        app.register_blueprint(bp)
        return bp
