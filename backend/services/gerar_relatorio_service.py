"""Caso de uso: gerar o relatório de destinos mais salvos e estatísticas do app."""
from backend.repositories.lugar_repository import LugarRepository
from backend.repositories.relatorio_repository import RelatorioRepository


class GerarRelatorioService:
    def __init__(self, repositorio=None, repositorio_lugares=None):
        self.repositorio = repositorio or RelatorioRepository()
        self.repositorio_lugares = repositorio_lugares or LugarRepository()

    def executar(self, limite=10):
        return {
            "ranking_destinos": self.repositorio.ranking_destinos_mais_salvos(limite),
            "interesses_mais_escolhidos": self.repositorio.interesses_mais_escolhidos(),
            "lugares_por_categoria": self.repositorio_lugares.contar_por_categoria(),
            "estatisticas": self.repositorio.estatisticas_gerais(),
        }
