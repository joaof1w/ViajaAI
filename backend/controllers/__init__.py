"""Controllers: uma classe por recurso/Model do sistema."""
from backend.controllers.auth_controller import AuthController
from backend.controllers.avaliacao_controller import AvaliacaoController
from backend.controllers.calendario_controller import CalendarioController
from backend.controllers.chat_controller import ChatController
from backend.controllers.checklist_controller import ChecklistController
from backend.controllers.comparador_controller import ComparadorController
from backend.controllers.despesa_controller import DespesaController
from backend.controllers.diario_controller import DiarioController
from backend.controllers.favorito_controller import FavoritoController
from backend.controllers.foto_controller import FotoController
from backend.controllers.grupo_controller import GrupoController
from backend.controllers.lugar_controller import LugarController
from backend.controllers.mapa_controller import MapaController
from backend.controllers.preferencia_controller import PreferenciaController
from backend.controllers.relatorio_controller import RelatorioController
from backend.controllers.roteiro_controller import RoteiroController
from backend.controllers.usuario_controller import UsuarioController
from backend.controllers.viagem_controller import ViagemController

CONTROLLERS = [
    AuthController,
    UsuarioController,
    PreferenciaController,
    LugarController,
    FavoritoController,
    ChatController,
    RelatorioController,
    # --- expansão ---
    ViagemController,
    RoteiroController,
    DespesaController,
    ChecklistController,
    CalendarioController,
    GrupoController,
    AvaliacaoController,
    DiarioController,
    FotoController,
    MapaController,
    ComparadorController,
]

__all__ = [c.__name__ for c in CONTROLLERS] + ["CONTROLLERS"]
