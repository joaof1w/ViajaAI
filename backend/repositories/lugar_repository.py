"""Consultas especiais de Lugar (filtros combinados, popularidade e candidatos à recomendação).

O CRUD simples continua na Model; aqui ficam apenas as consultas complexas.
Em MySQL, as Stored Procedures equivalentes (backend/sql/procedures_mysql.sql) devem ser
chamadas por este mesmo Repository — nunca pela Controller ou pelo Service.
"""
from sqlalchemy import text

from backend.extensions import db
from backend.models.lugar import Lugar


class LugarRepository:
    """Repository de acesso a dados de lugares."""

    def __init__(self, sessao=None):
        self.sessao = sessao or db.session

    # ------------------------------------------------------------------
    # Consulta com filtros combinados + popularidade (nº de vezes salvo)
    # ------------------------------------------------------------------
    def buscar_com_filtros(
        self,
        categoria=None,
        texto=None,
        faixa_preco_maxima=None,
        estado=None,
        nota_minima=None,
        ordenar_por="nota",
        limite=60,
    ):
        sql = """
            SELECT l.id AS id, COUNT(f.id) AS popularidade
              FROM lugares l
         LEFT JOIN favoritos f ON f.lugar_id = l.id
             WHERE 1 = 1
        """
        parametros = {"limite": int(limite)}

        if categoria and categoria != "todos":
            sql += " AND l.categoria = :categoria"
            parametros["categoria"] = categoria
        if texto:
            sql += " AND (LOWER(l.nome) LIKE :texto OR LOWER(l.cidade) LIKE :texto"
            sql += " OR LOWER(l.descricao) LIKE :texto)"
            parametros["texto"] = f"%{texto.strip().lower()}%"
        if faixa_preco_maxima:
            sql += " AND l.faixa_preco <= :faixa"
            parametros["faixa"] = int(faixa_preco_maxima)
        if estado:
            sql += " AND l.estado = :estado"
            parametros["estado"] = estado.upper()
        if nota_minima:
            sql += " AND l.nota >= :nota"
            parametros["nota"] = float(nota_minima)

        ordenacoes = {
            "nota": "l.nota DESC, l.avaliacoes DESC",
            "populares": "popularidade DESC, l.nota DESC",
            "preco": "l.faixa_preco ASC, l.nota DESC",
            "nome": "l.nome ASC",
        }
        sql += " GROUP BY l.id ORDER BY " + ordenacoes.get(ordenar_por, ordenacoes["nota"])
        sql += " LIMIT :limite"

        linhas = self.sessao.execute(text(sql), parametros).mappings().all()
        return self._hidratar(linhas)

    # ------------------------------------------------------------------
    # Candidatos para o motor de recomendação
    # ------------------------------------------------------------------
    def buscar_candidatos_para_recomendacao(self, categorias, faixa_preco_maxima=None, limite=80):
        """Traz lugares das categorias de interesse (ou todos) com sua popularidade."""
        sql = """
            SELECT l.id AS id, COUNT(f.id) AS popularidade
              FROM lugares l
         LEFT JOIN favoritos f ON f.lugar_id = l.id
             WHERE 1 = 1
        """
        parametros = {"limite": int(limite)}

        if categorias:
            marcadores = ", ".join(f":cat{i}" for i in range(len(categorias)))
            sql += f" AND l.categoria IN ({marcadores})"
            for i, cat in enumerate(categorias):
                parametros[f"cat{i}"] = cat
        if faixa_preco_maxima:
            sql += " AND l.faixa_preco <= :faixa"
            parametros["faixa"] = int(faixa_preco_maxima) + 1  # tolera uma faixa acima

        sql += " GROUP BY l.id ORDER BY l.nota DESC, popularidade DESC LIMIT :limite"
        linhas = self.sessao.execute(text(sql), parametros).mappings().all()
        return self._hidratar(linhas)

    # ------------------------------------------------------------------
    def contar_por_categoria(self):
        sql = """
            SELECT l.categoria AS categoria, COUNT(*) AS total, AVG(l.nota) AS nota_media
              FROM lugares l
          GROUP BY l.categoria
          ORDER BY total DESC
        """
        return [
            {
                "categoria": linha["categoria"],
                "total": linha["total"],
                "nota_media": round(float(linha["nota_media"] or 0), 2),
            }
            for linha in self.sessao.execute(text(sql)).mappings().all()
        ]

    def listar_estados_disponiveis(self):
        sql = "SELECT DISTINCT estado FROM lugares ORDER BY estado"
        return [linha["estado"] for linha in self.sessao.execute(text(sql)).mappings().all()]

    # ------------------------------------------------------------------
    def _hidratar(self, linhas):
        """Converte as linhas (id, popularidade) em objetos Lugar preservando a ordem."""
        ids = [linha["id"] for linha in linhas]
        if not ids:
            return []
        populares = {linha["id"]: int(linha["popularidade"] or 0) for linha in linhas}
        objetos = {
            lugar.id: lugar
            for lugar in self.sessao.query(Lugar).filter(Lugar.id.in_(ids)).all()
        }
        resultado = []
        for identificador in ids:
            lugar = objetos.get(identificador)
            if lugar is not None:
                lugar.popularidade = populares.get(identificador, 0)
                resultado.append(lugar)
        return resultado
