"""Migrações seguras do banco (não destrutivas).

Regras: nunca remover tabelas/colunas nem apagar dados; apenas criar o que falta.
Cada migração roda uma única vez e fica registrada em `migracoes_aplicadas`, o que
mantém bancos existentes (SQLite ou MySQL) compatíveis com a nova versão.
"""
from sqlalchemy import inspect, text

from backend.extensions import db
from backend.models.migracao import MigracaoAplicada

TABELAS_EXPANSAO = [
    "viagens", "participantes_viagem", "roteiros", "atividades_roteiro", "despesas", "planejamento_orcamento",
    "itens_checklist", "compromissos", "sugestoes_viagem", "votos_sugestao", "avaliacoes", "fotos_avaliacao",
    "registros_diario", "fotos_diario", "fotos_lugar", "pontos_interesse", "cache_externo", "permissoes_assistente",
]


def adicionar_coluna_se_ausente(tabela, coluna, definicao_sql):
    """Adiciona uma coluna nova (sempre anulável ou com padrão) se ela ainda não existir."""
    colunas = {c["name"] for c in inspect(db.engine).get_columns(tabela)}
    if coluna not in colunas:
        db.session.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao_sql}"))
        db.session.commit()


def _m001_tabelas_da_expansao():
    tabelas = [db.metadata.tables[nome] for nome in TABELAS_EXPANSAO]
    db.metadata.create_all(db.engine, tables=tabelas, checkfirst=True)


MIGRACOES = [
    ("2026_11_001_tabelas_expansao_12_funcionalidades", _m001_tabelas_da_expansao),
]


def aplicar_migracoes():
    MigracaoAplicada.__table__.create(db.engine, checkfirst=True)
    aplicadas = {m.nome for m in db.session.query(MigracaoAplicada).all()}
    executadas = []
    for nome, funcao in MIGRACOES:
        if nome in aplicadas:
            continue
        funcao()
        db.session.add(MigracaoAplicada(nome=nome))
        db.session.commit()
        executadas.append(nome)
    return executadas
