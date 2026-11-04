-- ---------------------------------------------------------------------------
-- Stored Procedures (opcional — usadas quando DATABASE_URL aponta para MySQL).
-- O CALL fica encapsulado em backend/repositories/relatorio_repository.py.
-- Controllers e Services nunca executam SQL nem chamam procedures diretamente.
--
-- Execute uma vez no banco:  mysql -u usuario -p viajai < backend/sql/procedures_mysql.sql
-- ---------------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_ranking_destinos;

DELIMITER $$

CREATE PROCEDURE sp_ranking_destinos(IN p_limite INT)
BEGIN
    SELECT l.id           AS id,
           l.nome         AS nome,
           l.categoria    AS categoria,
           l.cidade       AS cidade,
           l.estado       AS estado,
           l.nota         AS nota,
           COUNT(f.id)    AS total_salvos
      FROM lugares l
 LEFT JOIN favoritos f ON f.lugar_id = l.id
  GROUP BY l.id, l.nome, l.categoria, l.cidade, l.estado, l.nota
  ORDER BY total_salvos DESC, l.nota DESC
     LIMIT p_limite;
END$$

DELIMITER ;
