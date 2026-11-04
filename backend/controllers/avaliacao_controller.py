"""Controller do recurso Avaliacao (avaliações e experiências da comunidade)."""
from flask import Blueprint, g, jsonify, request

from backend.services.avaliacoes_service import (
    CriarAvaliacaoService,
    EditarAvaliacaoService,
    ExcluirAvaliacaoService,
    ListarAvaliacoesLugarService,
    ListarComunidadeService,
    RemoverFotoAvaliacaoService,
)
from backend.utils.autenticacao import login_obrigatorio, usuario_do_token
from backend.utils.limite_requisicoes import limitar
from backend.utils.requisicao import dados_e_fotos


class AvaliacaoController:
    def __init__(self):
        self.listar_avaliacoes_lugar_service = ListarAvaliacoesLugarService()
        self.criar_avaliacao_service = CriarAvaliacaoService()
        self.editar_avaliacao_service = EditarAvaliacaoService()
        self.excluir_avaliacao_service = ExcluirAvaliacaoService()
        self.remover_foto_avaliacao_service = RemoverFotoAvaliacaoService()
        self.listar_comunidade_service = ListarComunidadeService()

    def listar(self, lugar_id):
        ordenar = request.args.get("ordenar", "recentes")
        return jsonify(self.listar_avaliacoes_lugar_service.executar(lugar_id, usuario_do_token(), ordenar)), 200

    def criar(self, lugar_id):
        dados, fotos = dados_e_fotos()
        return jsonify(self.criar_avaliacao_service.executar(lugar_id, g.usuario, dados, fotos)), 201

    def editar(self, avaliacao_id):
        dados, fotos = dados_e_fotos()
        return jsonify(self.editar_avaliacao_service.executar(avaliacao_id, g.usuario, dados, fotos)), 200

    def excluir(self, avaliacao_id):
        return jsonify(self.excluir_avaliacao_service.executar(avaliacao_id, g.usuario)), 200

    def remover_foto(self, avaliacao_id, foto_id):
        return jsonify(self.remover_foto_avaliacao_service.executar(avaliacao_id, foto_id, g.usuario)), 200

    def comunidade(self):
        return jsonify(self.listar_comunidade_service.executar(usuario_do_token())), 200

    def registrar(self, app):
        bp = Blueprint("avaliacoes", __name__, url_prefix="/api")
        p = login_obrigatorio
        bp.add_url_rule("/lugares/<int:lugar_id>/avaliacoes", view_func=self.listar, methods=["GET"])
        bp.add_url_rule("/lugares/<int:lugar_id>/avaliacoes",
                        view_func=p(limitar("avaliar", 10, 3600)(self.criar)), methods=["POST"])
        bp.add_url_rule("/avaliacoes/<int:avaliacao_id>", view_func=p(limitar("editar_avaliacao", 30, 3600)(self.editar)),
                        methods=["PUT", "POST"])
        bp.add_url_rule("/avaliacoes/<int:avaliacao_id>", view_func=p(self.excluir), methods=["DELETE"])
        bp.add_url_rule("/avaliacoes/<int:avaliacao_id>/fotos/<int:foto_id>", view_func=p(self.remover_foto),
                        methods=["DELETE"])
        bp.add_url_rule("/comunidade", view_func=self.comunidade, methods=["GET"])
        app.register_blueprint(bp)
        return bp
