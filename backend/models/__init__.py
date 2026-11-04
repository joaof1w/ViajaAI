"""Models do domínio Viajaí."""
from backend.models.codigo_verificacao import CodigoVerificacao
from backend.models.favorito import Favorito
from backend.models.interesse import Interesse, preferencia_interesses
from backend.models.lugar import Lugar
from backend.models.mensagem_chat import MensagemChat
from backend.models.preferencia import FAIXAS_ORCAMENTO, Preferencia
from backend.models.usuario import Usuario

__all__ = [
    "CodigoVerificacao",
    "Favorito",
    "Interesse",
    "preferencia_interesses",
    "Lugar",
    "MensagemChat",
    "Preferencia",
    "FAIXAS_ORCAMENTO",
    "Usuario",
]
