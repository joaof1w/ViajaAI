"""Consultas de relatório/ranking — SQL agregado que não pertence ao CRUD das Models.

Se o banco for MySQL, o CALL da Stored Procedure `sp_ranking_destinos`
(backend/sql/procedures_mysql.sql) fica encapsulado aqui.
"""
from sqlalchemy import text

from backend.config import Config
from backend.extensions import db


class RelatorioRepository:
    def __init__(self, sessao=None):
        self.sessao = sessao or db.session

    @property
    def usando_mysql(self):
        return Config.SQLALCHEMY_DATABASE_URI.startswith("mysql")

    # ------------------------------------------------------------------
    def ranking_destinos_mais_salvos(self, limite=10):
        """Ranking dos lugares mais salvos pelos usuários."""
        if self.usando_mysql:
            # Stored Procedure encapsulada no Repository
            linhas = self.sessao.execute(
                text("CALL sp_ranking_destinos(:limite)"), {"limite": int(limite)}
            ).mappings().all()
        else:
            sql = """
                SELECT l.id            AS id,
                       l.nome          AS nome,
                       l.categoria     AS categoria,
                       l.cidade        AS cidade,
                       l.estado        AS estado,
                       l.nota          AS nota,
                       COUNT(f.id)     AS total_salvos
                  FROM lugares l
             LEFT JOIN favoritos f ON f.lugar_id = l.id
              GROUP BY l.id, l.nome, l.categoria, l.cidade, l.estado, l.nota
              ORDER BY total_salvos DESC, l.nota DESC
                 LIMIT :limite
            """
            linhas = self.sessao.execute(text(sql), {"limite": int(limite)}).mappings().all()

        return [
            {
                "posicao": posicao,
                "id": linha["id"],
                "nome": linha["nome"],
                "categoria": linha["categoria"],
                "local": f'{linha["cidade"]}, {linha["estado"]}',
                "nota": round(float(linha["nota"]), 1),
                "total_salvos": int(linha["total_salvos"] or 0),
            }
            for posicao, linha in enumerate(linhas, start=1)
        ]

    # ------------------------------------------------------------------
    def interesses_mais_escolhidos(self):
        sql = """
            SELECT i.nome AS nome, i.slug AS slug, COUNT(pi.preferencia_id) AS total
              FROM interesses i
         LEFT JOIN preferencia_interesses pi ON pi.interesse_id = i.id
          GROUP BY i.id, i.nome, i.slug
          ORDER BY total DESC, i.nome ASC
        """
        return [
            {"slug": linha["slug"], "nome": linha["nome"], "total": int(linha["total"] or 0)}
            for linha in self.sessao.execute(text(sql)).mappings().all()
        ]

    def estatisticas_gerais(self):
        sql = """
            SELECT (SELECT COUNT(*) FROM usuarios)        AS usuarios,
                   (SELECT COUNT(*) FROM usuarios WHERE verificado = 1) AS usuarios_verificados,
                   (SELECT COUNT(*) FROM lugares)         AS lugares,
                   (SELECT COUNT(*) FROM favoritos)       AS favoritos,
                   (SELECT COUNT(*) FROM mensagens_chat)  AS mensagens
        """
        linha = self.sessao.execute(text(sql)).mappings().first()
        return {chave: int(valor or 0) for chave, valor in dict(linha).items()}
