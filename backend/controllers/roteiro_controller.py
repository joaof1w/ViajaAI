"""Controller dos recursos Roteiro e AtividadeRoteiro (roteiros inteligentes)."""
from flask import Blueprint, g, jsonify

from backend.services.roteiros_service import (
    AdicionarAtividadeService,
    AtivarRoteiroService,
    CriarRoteiroManualService,
    DuplicarRoteiroService,
    EditarAtividadeService,
    ExcluirAtividadeService,
    ExcluirRoteiroService,
    GerarRoteiroService,
    ListarRoteirosService,
    ObterRoteiroService,
    ReorganizarAtividadesService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar
from backend.utils.requisicao import corpo_json


class RoteiroController:
    def __init__(self):
        self.listar_roteiros_service = ListarRoteirosService()
        self.gerar_roteiro_service = GerarRoteiroService()
        self.criar_roteiro_manual_service = CriarRoteiroManualService()
        self.obter_roteiro_service = ObterRoteiroService()
        self.duplicar_roteiro_service = DuplicarRoteiroService()
        self.ativar_roteiro_service = AtivarRoteiroService()
        self.excluir_roteiro_service = ExcluirRoteiroService()
        self.reorganizar_atividades_service = ReorganizarAtividadesService()
        self.adicionar_atividade_service = AdicionarAtividadeService()
        self.editar_atividade_service = EditarAtividadeService()
        self.excluir_atividade_service = ExcluirAtividadeService()

    def listar(self, viagem_id):
        return jsonify(self.listar_roteiros_service.executar(viagem_id, g.usuario)), 200

    def gerar(self, viagem_id):
        return jsonify(self.gerar_roteiro_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def criar_manual(self, viagem_id):
        return jsonify(self.criar_roteiro_manual_service.executar(viagem_id, g.usuario, corpo_json())), 201

    def detalhar(self, roteiro_id):
        return jsonify(self.obter_roteiro_service.executar(roteiro_id, g.usuario)), 200

    def duplicar(self, roteiro_id):
        return jsonify(self.duplicar_roteiro_service.executar(roteiro_id, g.usuario)), 201

    def ativar(self, roteiro_id):
        return jsonify(self.ativar_roteiro_service.executar(roteiro_id, g.usuario)), 200

    def excluir(self, roteiro_id):
        return jsonify(self.excluir_roteiro_service.executar(roteiro_id, g.usuario)), 200

    def reorganizar(self, roteiro_id):
        return jsonify(self.reorganizar_atividades_service.executar(roteiro_id, g.usuario, corpo_json())), 200

    def adicionar_atividade(self, roteiro_id):
        return jsonify(self.adicionar_atividade_service.executar(roteiro_id, g.usuario, corpo_json())), 201

    def editar_atividade(self, atividade_id):
        return jsonify(self.editar_atividade_service.executar(atividade_id, g.usuario, corpo_json())), 200

    def excluir_atividade(self, atividade_id):
        return jsonify(self.excluir_atividade_service.executar(atividade_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("roteiros", __name__, url_prefix="/api")
        protegido = login_obrigatorio
        bp.add_url_rule("/viagens/<int:viagem_id>/roteiros", view_func=protegido(self.listar), methods=["GET"])
        bp.add_url_rule("/viagens/<int:viagem_id>/roteiros", view_func=protegido(self.criar_manual), methods=["POST"])
        bp.add_url_rule("/viagens/<int:viagem_id>/roteiros/gerar",
                        view_func=protegido(limitar("gerar_roteiro", 8, 60)(self.gerar)), methods=["POST"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>", view_func=protegido(self.detalhar), methods=["GET"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>", view_func=protegido(self.excluir), methods=["DELETE"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>/duplicar", view_func=protegido(self.duplicar), methods=["POST"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>/ativar", view_func=protegido(self.ativar), methods=["POST"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>/ordem", view_func=protegido(self.reorganizar), methods=["PUT"])
        bp.add_url_rule("/roteiros/<int:roteiro_id>/atividades", view_func=protegido(self.adicionar_atividade),
                        methods=["POST"])
        bp.add_url_rule("/atividades/<int:atividade_id>", view_func=protegido(self.editar_atividade),
                        methods=["PUT", "PATCH"])
        bp.add_url_rule("/atividades/<int:atividade_id>", view_func=protegido(self.excluir_atividade),
                        methods=["DELETE"])
        app.register_blueprint(bp)
        return bp
