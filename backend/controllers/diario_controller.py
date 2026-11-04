"""Controller do recurso RegistroDiario (histórico e diário de viagens)."""
from flask import Blueprint, g, jsonify

from backend.services.diario_service import (
    CriarRegistroDiarioService,
    EditarRegistroDiarioService,
    EstatisticasViagemService,
    ExcluirRegistroDiarioService,
    ListarDiarioDaViagemService,
    ListarDiarioService,
    RemoverFotoDiarioService,
)
from backend.utils.autenticacao import login_obrigatorio
from backend.utils.limite_requisicoes import limitar
from backend.utils.requisicao import dados_e_fotos


class DiarioController:
    def __init__(self):
        self.listar_diario_service = ListarDiarioService()
        self.criar_registro_diario_service = CriarRegistroDiarioService()
        self.editar_registro_diario_service = EditarRegistroDiarioService()
        self.excluir_registro_diario_service = ExcluirRegistroDiarioService()
        self.remover_foto_diario_service = RemoverFotoDiarioService()
        self.estatisticas_viagem_service = EstatisticasViagemService()
        self.listar_diario_da_viagem_service = ListarDiarioDaViagemService()

    def listar(self):
        return jsonify(self.listar_diario_service.executar(g.usuario)), 200

    def criar(self):
        dados, fotos = dados_e_fotos()
        return jsonify(self.criar_registro_diario_service.executar(g.usuario, dados, fotos)), 201

    def editar(self, registro_id):
        dados, fotos = dados_e_fotos()
        return jsonify(self.editar_registro_diario_service.executar(registro_id, g.usuario, dados, fotos)), 200

    def excluir(self, registro_id):
        return jsonify(self.excluir_registro_diario_service.executar(registro_id, g.usuario)), 200

    def remover_foto(self, registro_id, foto_id):
        return jsonify(self.remover_foto_diario_service.executar(registro_id, foto_id, g.usuario)), 200

    def estatisticas(self):
        return jsonify(self.estatisticas_viagem_service.executar(g.usuario)), 200

    def da_viagem(self, viagem_id):
        return jsonify(self.listar_diario_da_viagem_service.executar(viagem_id, g.usuario)), 200

    def registrar(self, app):
        bp = Blueprint("diario", __name__, url_prefix="/api")
        p = login_obrigatorio
        bp.add_url_rule("/diario", view_func=p(self.listar), methods=["GET"])
        bp.add_url_rule("/diario", view_func=p(limitar("diario", 40, 3600)(self.criar)), methods=["POST"])
        bp.add_url_rule("/diario/estatisticas", view_func=p(self.estatisticas), methods=["GET"])
        bp.add_url_rule("/diario/<int:registro_id>", view_func=p(limitar("diario_editar", 60, 3600)(self.editar)),
                        methods=["PUT", "POST"])
        bp.add_url_rule("/diario/<int:registro_id>", view_func=p(self.excluir), methods=["DELETE"])
        bp.add_url_rule("/diario/<int:registro_id>/fotos/<int:foto_id>", view_func=p(self.remover_foto),
                        methods=["DELETE"])
        bp.add_url_rule("/viagens/<int:viagem_id>/diario", view_func=p(self.da_viagem), methods=["GET"])
        app.register_blueprint(bp)
        return bp
