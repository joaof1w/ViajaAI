"""Integração externa com a LLM (Google Gemini), encapsulada em um Service próprio.

A chave da API nunca fica no código: vem de GEMINI_API_KEY no .env.
Se a chave não estiver configurada — ou se a chamada externa falhar — a resposta
é gerada pelo AssistenteLocalService, de modo que o chat continue funcionando.
"""
import json

import requests

from backend.config import Config
from backend.services.assistente_local_service import AssistenteLocalService

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

INSTRUCAO = (
    "Você é o Vai, assistente de viagens do aplicativo Viajaí. Responda sempre em "
    "português do Brasil, em no máximo 6 linhas, com tom simpático e objetivo. "
    "Use os dados do perfil, as viagens, roteiros, agenda, gastos e memórias fornecidos (apenas os "
    "que o usuário autorizou) para personalizar a resposta e cite os nomes dos lugares quando fizer "
    "sentido. Ajude a criar e organizar viagens. Não invente preços, horários de funcionamento, "
    "disponibilidade ou estabelecimentos: se não souber, diga que não há dados confirmados."
)


INSTRUCAO_PLANEJADOR = (
    "Você é o Vai, planejador de viagens do Viajaí. Organize roteiros usando apenas os lugares "
    "fornecidos, sem inventar estabelecimentos, preços, horários de funcionamento ou disponibilidade. "
    "Responda somente com JSON válido."
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
    def gerar_json(self, prompt, max_tokens=2048):
        """Pede uma resposta estruturada (JSON). Devolve dict/list ou None em qualquer falha."""
        if not self.configurado:
            return None
        try:
            resposta = requests.post(
                URL_BASE.format(modelo=self.config.GEMINI_MODEL),
                params={"key": self.config.GEMINI_API_KEY},
                json={
                    "system_instruction": {"parts": [{"text": INSTRUCAO_PLANEJADOR}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": max_tokens,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=max(self.config.GEMINI_TIMEOUT, 30),
            )
            resposta.raise_for_status()
            partes = resposta.json()["candidates"][0]["content"]["parts"]
            texto = "".join(parte.get("text", "") for parte in partes).strip()
            texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(texto)
        except Exception as erro:
            print(f"[GeminiService] falha ao gerar JSON: {erro}", flush=True)
            return None

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
        extras = []
        for viagem in contexto.get("viagens", []):
            linha = (f"- {'[EM FOCO] ' if viagem.get('foco') else ''}{viagem['titulo']} → {viagem['destino']}, "
                     f"{viagem['data_ida']} a {viagem['data_volta']} ({viagem['duracao_dias']} dias, "
                     f"{viagem['viajantes']} viajante(s), status {viagem['status']})")
            if viagem.get("roteiro"):
                linha += "; roteiro: " + "; ".join(
                    f"dia {a['dia']} {a['horario'] or ''} {a['titulo']}".strip() for a in viagem["roteiro"][:12])
            if viagem.get("agenda"):
                linha += "; agenda: " + "; ".join(f"{e['inicio']} {e['titulo']}" for e in viagem["agenda"][:8])
            if viagem.get("conflitos"):
                linha += f"; {viagem['conflitos']} conflito(s) de horário"
            if viagem.get("financas"):
                f = viagem["financas"]
                linha += f"; orçamento R$ {f['orcamento']}, gasto R$ {f['gasto']}, saldo R$ {f['saldo']}"
            if viagem.get("checklist"):
                c = viagem["checklist"]
                linha += f"; checklist {c['concluidos']}/{c['total']}"
            extras.append(linha)
        if contexto.get("favoritos"):
            extras.append("Favoritos: " + ", ".join(f["nome"] for f in contexto["favoritos"]))
        if contexto.get("diario"):
            extras.append("Memórias recentes: " + "; ".join(
                f"{d['titulo']} ({d['local'] or ''}, {d['data']})" for d in contexto["diario"]))
        return (
            f"Perfil do usuário:\n"
            f"- Nome: {contexto.get('nome')}\n"
            f"- Cidade: {contexto.get('cidade')} ({contexto.get('estado')})\n"
            f"- Interesses: {', '.join(contexto.get('interesses', [])) or 'não informados'}\n"
            f"- Orçamento: {contexto.get('orcamento_rotulo')}\n\n"
            f"Lugares recomendados pelo app:\n{lugares or 'nenhum'}\n\n"
            f"Dados autorizados de viagem:\n{chr(10).join(extras) or 'nenhum (o usuário não autorizou ou não há viagens)'}\n\n"
            f"Pergunta do usuário: {pergunta}"
        )
