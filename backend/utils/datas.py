"""Data e hora do sistema.

Usamos UTC "ingênuo" (sem fuso embutido) porque é assim que o SQLite devolve as
datas gravadas — misturar datas com e sem fuso quebraria as comparações.
`datetime.utcnow()` está obsoleto a partir do Python 3.12, então centralizamos
a chamada aqui.
"""
from datetime import datetime, timezone


def agora_utc():
    """Momento atual em UTC, sem informação de fuso."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hoje():
    """Data local de hoje (as viagens são planejadas em datas do calendário local)."""
    from datetime import date

    return date.today()


def formatar_data(valor):
    return valor.isoformat() if valor else None
