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
