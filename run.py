"""Ponto de entrada: python run.py"""
from backend.app import create_app
from backend.config import Config

app = create_app()

if __name__ == "__main__":
    print(f"\n➜  Viajaí rodando em http://localhost:{Config.PORT}\n")
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
