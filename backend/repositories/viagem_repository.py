"""Consultas especiais de Viagem (viagens do usuário, resumos agregados, verificação)."""
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from backend.extensions import db
from backend.models.checklist import ItemChecklist
from backend.models.compromisso import Compromisso
from backend.models.despesa import Despesa
from backend.models.roteiro import AtividadeRoteiro, Roteiro
from backend.models.viagem import ParticipanteViagem, Viagem


class ViagemRepository:
    def __init__(self, sessao=None):
        self.sessao = sessao or db.session

    def listar_do_usuario(self, usuario_id):
        """Viagens que o usuário organiza ou das quais participa (convite aceito)."""
        participa = (
            self.sessao.query(ParticipanteViagem.viagem_id)
            .filter(ParticipanteViagem.usuario_id == usuario_id, ParticipanteViagem.status == "aceito")
        )
        return (
            self.sessao.query(Viagem)
            .options(selectinload(Viagem.participantes), selectinload(Viagem.lugar))
            .filter(or_(Viagem.proprietario_id == usuario_id, Viagem.id.in_(participa)))
            .all()
        )

    def resumo(self, viagem):
        gasto = self.sessao.query(func.coalesce(func.sum(Despesa.valor_centavos), 0)).filter(
            Despesa.viagem_id == viagem.id).scalar()
        itens = self.sessao.query(func.count(ItemChecklist.id), func.sum(
            db.case((ItemChecklist.concluido.is_(True), 1), else_=0))).filter(
            ItemChecklist.viagem_id == viagem.id).one()
        total_itens, concluidos = int(itens[0] or 0), int(itens[1] or 0)
        compromissos = self.sessao.query(func.count(Compromisso.id)).filter(
            Compromisso.viagem_id == viagem.id).scalar()
        roteiro = viagem.roteiro_ativo
        return {
            "gasto": int(gasto or 0) / 100,
            "orcamento": viagem.orcamento_centavos / 100 if viagem.orcamento_centavos is not None else None,
            "checklist_total": total_itens,
            "checklist_concluidos": concluidos,
            "checklist_percentual": round(concluidos * 100 / total_itens) if total_itens else 0,
            "compromissos": int(compromissos or 0),
            "roteiro_versoes": len(viagem.roteiros),
            "roteiro_atividades": len(roteiro.atividades) if roteiro else 0,
        }

    def viagem_concluida_com_lugar(self, usuario_id, lugar_id, hoje):
        """Primeira viagem concluída do usuário cujo destino ou roteiro ativo inclui o lugar."""
        participa = (
            self.sessao.query(ParticipanteViagem.viagem_id)
            .filter(ParticipanteViagem.usuario_id == usuario_id, ParticipanteViagem.status == "aceito")
        )
        no_roteiro = (
            self.sessao.query(Roteiro.viagem_id)
            .join(AtividadeRoteiro, AtividadeRoteiro.roteiro_id == Roteiro.id)
            .filter(Roteiro.ativo.is_(True), AtividadeRoteiro.lugar_id == lugar_id)
        )
        return (
            self.sessao.query(Viagem)
            .filter(
                or_(Viagem.proprietario_id == usuario_id, Viagem.id.in_(participa)),
                Viagem.data_volta < hoje,
                or_(Viagem.lugar_id == lugar_id, Viagem.id.in_(no_roteiro)),
            )
            .order_by(Viagem.data_volta.desc())
            .first()
        )
