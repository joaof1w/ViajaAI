"""Controllers: uma classe por recurso/Model do sistema."""
from backend.controllers.auth_controller import AuthController
from backend.controllers.chat_controller import ChatController
from backend.controllers.favorito_controller import FavoritoController
from backend.controllers.lugar_controller import LugarController
from backend.controllers.preferencia_controller import PreferenciaController
from backend.controllers.relatorio_controller import RelatorioController
from backend.controllers.usuario_controller import UsuarioController

CONTROLLERS = [
    AuthController,
    UsuarioController,
    PreferenciaController,
    LugarController,
    FavoritoController,
    ChatController,
    RelatorioController,
]

__all__ = [c.__name__ for c in CONTROLLERS] + ["CONTROLLERS"]
