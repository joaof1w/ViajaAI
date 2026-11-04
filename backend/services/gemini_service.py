"""Integração externa com a LLM (Google Gemini), encapsulada em um Service próprio.

A chave da API nunca fica no código: vem de GEMINI_API_KEY no .env.
Se a chave não estiver configurada — ou se a chamada externa falhar — a resposta
é gerada pelo AssistenteLocalService, de modo que o chat continue funcionando.
"""
import requests

from backend.config import Config
from backend.services.assistente_local_service import AssistenteLocalService

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

INSTRUCAO = (
    "Você é o Vai, assistente de viagens do aplicativo Viajaí. Responda sempre em "
    "português do Brasil, em no máximo 6 linhas, com tom simpático e objetivo. "
    "Use os dados do perfil e a lista de lugares fornecidos para personalizar a resposta "
    "e cite os nomes dos lugares quando fizer sentido. Não invente preços exatos."
)


class GeminiService:
    def __init__(self, config=None, servico_local=None):
        self.config = config or Config
        self.servico_local = servico_local or AssistenteLocalService()

    @property
    def configurado(self):
        return bool(self.config.GEMINI_API_KEY)

    # ------------------------------------------------------------------
    def executar(self, pergunta, contexto, historico=None):
        if not self.configurado:
            return {"texto": self.servico_local.executar(pergunta, contexto), "origem": "local"}
        try:
            texto = self._chamar_api(pergunta, contexto, historico or [])
            if not texto:
                raise ValueError("Resposta vazia da API")
            return {"texto": texto.strip(), "origem": "gemini"}
        except Exception as erro:  # falha de rede, cota, chave inválida...
            print(f"[GeminiService] falha na API externa: {erro}", flush=True)
            return {"texto": self.servico_local.executar(pergunta, contexto), "origem": "local"}

    # ------------------------------------------------------------------
    def _chamar_api(self, pergunta, contexto, historico):
        conteudos = []
        for mensagem in historico[-6:]:
            conteudos.append(
                {
                    "role": "user" if mensagem["autor"] == "usuario" else "model",
                    "parts": [{"text": mensagem["texto"]}],
                }
            )
        conteudos.append({"role": "user", "parts": [{"text": self._montar_prompt(pergunta, contexto)}]})

        resposta = requests.post(
            URL_BASE.format(modelo=self.config.GEMINI_MODEL),
            params={"key": self.config.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": INSTRUCAO}]},
                "contents": conteudos,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400},
            },
            timeout=self.config.GEMINI_TIMEOUT,
        )
        resposta.raise_for_status()
        dados = resposta.json()
        partes = dados["candidates"][0]["content"]["parts"]
        return "".join(parte.get("text", "") for parte in partes)

    @staticmethod
    def _montar_prompt(pergunta, contexto):
        lugares = "\n".join(
            f"- {l['nome']} ({l['categoria']}, {l['local']}): nota {l['nota']}, "
            f"preço {l['preco_simbolo']}, {l['match']}% de match, "
            f"{l.get('distancia_km', 0)} km do usuário. {l['descricao']}"
            for l in contexto.get("lugares", [])[:8]
        )
        return (
            f"Perfil do usuário:\n"
            f"- Nome: {contexto.get('nome')}\n"
            f"- Cidade: {contexto.get('cidade')} ({contexto.get('estado')})\n"
            f"- Interesses: {', '.join(contexto.get('interesses', [])) or 'não informados'}\n"
            f"- Orçamento: {contexto.get('orcamento_rotulo')}\n\n"
            f"Lugares recomendados pelo app:\n{lugares or 'nenhum'}\n\n"
            f"Pergunta do usuário: {pergunta}"
        )
