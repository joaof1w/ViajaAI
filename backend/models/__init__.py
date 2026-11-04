"""Models do domínio Viajaí."""
from backend.models.avaliacao import Avaliacao, FotoAvaliacao
from backend.models.cache_externo import CacheExterno
from backend.models.checklist import CATEGORIAS_CHECKLIST, ItemChecklist
from backend.models.codigo_verificacao import CodigoVerificacao
from backend.models.compromisso import TIPOS_COMPROMISSO, Compromisso
from backend.models.despesa import CATEGORIAS_DESPESA, Despesa, PlanejamentoOrcamento
from backend.models.diario import VISIBILIDADES, FotoDiario, RegistroDiario
from backend.models.favorito import Favorito
from backend.models.foto_lugar import FONTES_FOTO, FotoLugar
from backend.models.interesse import Interesse, preferencia_interesses
from backend.models.lugar import Lugar
from backend.models.mensagem_chat import MensagemChat
from backend.models.migracao import MigracaoAplicada
from backend.models.permissao_assistente import ESCOPOS_ASSISTENTE, PermissaoAssistente
from backend.models.ponto_interesse import PontoInteresse
from backend.models.preferencia import FAIXAS_ORCAMENTO, Preferencia
from backend.models.roteiro import CATEGORIAS_ATIVIDADE, AtividadeRoteiro, Roteiro
from backend.models.sugestao import SugestaoViagem, VotoSugestao
from backend.models.usuario import Usuario
from backend.models.viagem import PAPEIS, TIPOS_VIAGEM, ParticipanteViagem, Viagem

__all__ = [
    "Avaliacao", "FotoAvaliacao", "CacheExterno", "CATEGORIAS_CHECKLIST", "ItemChecklist",
    "CodigoVerificacao", "TIPOS_COMPROMISSO", "Compromisso", "CATEGORIAS_DESPESA", "Despesa",
    "PlanejamentoOrcamento", "VISIBILIDADES", "FotoDiario", "RegistroDiario", "Favorito",
    "FONTES_FOTO", "FotoLugar", "Interesse", "preferencia_interesses", "Lugar", "MensagemChat",
    "MigracaoAplicada", "ESCOPOS_ASSISTENTE", "PermissaoAssistente", "PontoInteresse",
    "FAIXAS_ORCAMENTO", "Preferencia", "CATEGORIAS_ATIVIDADE", "AtividadeRoteiro", "Roteiro",
    "SugestaoViagem", "VotoSugestao", "Usuario", "PAPEIS", "TIPOS_VIAGEM", "ParticipanteViagem", "Viagem",
]
