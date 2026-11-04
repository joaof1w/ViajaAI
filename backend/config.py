"""Configuração da aplicação. Nada sensível fica no código: tudo vem do .env."""
import os

try:  # python-dotenv é opcional: sem ele, valem as variáveis do sistema
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "viajai-chave-de-desenvolvimento")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    PORT = int(os.getenv("PORT", 5000))

    # --- Banco de dados ---
    # Padrão: SQLite (não exige instalação de servidor).
    # Para MySQL basta trocar a DATABASE_URL no .env, ex.:
    # mysql+pymysql://usuario:senha@localhost:3306/viajai
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "backend", "viajai.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Integração com IA (Gemini) ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", 20))

    # --- Envio de e-mail (código de verificação) ---
    # Em desenvolvimento o código é impresso no terminal em vez de enviado.
    EMAIL_MODO = os.getenv("EMAIL_MODO", "console")  # console | smtp
    EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "nao-responda@viajai.app")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORTA = int(os.getenv("SMTP_PORTA", 587))
    SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
    SMTP_SENHA = os.getenv("SMTP_SENHA", "")

    # Regras de negócio configuráveis
    SENHA_TAMANHO_MINIMO = int(os.getenv("SENHA_TAMANHO_MINIMO", 6))
    CODIGO_VALIDADE_MINUTOS = int(os.getenv("CODIGO_VALIDADE_MINUTOS", 15))

    # --- Uploads de fotografias (avaliações e diário) ---
    PASTA_UPLOADS = os.getenv("PASTA_UPLOADS", os.path.join(BASE_DIR, "backend", "uploads"))
    UPLOAD_TAMANHO_MAXIMO_MB = int(os.getenv("UPLOAD_TAMANHO_MAXIMO_MB", 5))
    UPLOAD_MAXIMO_FOTOS = int(os.getenv("UPLOAD_MAXIMO_FOTOS", 6))
    UPLOAD_LADO_MAXIMO_PX = int(os.getenv("UPLOAD_LADO_MAXIMO_PX", 1920))
    # Limite do corpo da requisição (o Flask recusa com 413 acima disso)
    MAX_CONTENT_LENGTH = (UPLOAD_TAMANHO_MAXIMO_MB * UPLOAD_MAXIMO_FOTOS + 1) * 1024 * 1024
    URL_ARQUIVO_VALIDADE_MINUTOS = int(os.getenv("URL_ARQUIVO_VALIDADE_MINUTOS", 120))

    # --- Integrações externas (mapas, geocodificação, clima e fotografias) ---
    # 0 desliga todas as chamadas externas (útil em testes ou redes restritas).
    INTEGRACOES_EXTERNAS = os.getenv("INTEGRACOES_EXTERNAS", "1") == "1"
    # Wikimedia e Nominatim exigem um User-Agent que identifique a aplicação e um contato.
    HTTP_USER_AGENT = os.getenv(
        "HTTP_USER_AGENT", "Viajai/2.0 (aplicativo de viagens; configure HTTP_USER_AGENT com um contato)"
    )
    HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", 12))
    CACHE_EXTERNO_HORAS = int(os.getenv("CACHE_EXTERNO_HORAS", 24 * 7))
    NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    OPEN_METEO_URL = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
    WIKIPEDIA_API_URL = os.getenv("WIKIPEDIA_API_URL", "https://{idioma}.wikipedia.org/w/api.php")
    COMMONS_API_URL = os.getenv("COMMONS_API_URL", "https://commons.wikimedia.org/w/api.php")

    # Mapa (Leaflet + OpenStreetMap). Em produção use um provedor de tiles próprio/contratado.
    MAPA_TILE_URL = os.getenv("MAPA_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    MAPA_TILE_ATRIBUICAO = os.getenv(
        "MAPA_TILE_ATRIBUICAO",
        '&copy; <a href="https://www.openstreetmap.org/copyright">colaboradores do OpenStreetMap</a>',
    )

    # Fotografias dos lugares: Wikimedia Commons não exige chave; Pexels e Unsplash sim.
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
    # Busca as fotos reais em segundo plano ao iniciar (só para lugares ainda sem foto).
    FOTOS_SINCRONIZACAO_AUTOMATICA = os.getenv("FOTOS_SINCRONIZACAO_AUTOMATICA", "1") == "1"
