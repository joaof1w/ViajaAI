"""Motor dos Roteiros Inteligentes do Vai (feature 2).

Regras para não inventar informação:
- Só entram no roteiro lugares do catálogo do Viajaí ou pontos reais do OpenStreetMap
  (PontoInteresse). Quando faltam opções, o dia recebe "tempo livre" — nunca um
  estabelecimento fictício.
- Horários são SUGESTÕES de distribuição do dia (marcadas como tal). Horários de
  funcionamento só aparecem quando vêm do OpenStreetMap (tag opening_hours).
- Com Gemini configurado, a IA apenas escolhe e ordena itens da lista de candidatos;
  qualquer item fora da lista é descartado e, se nada sobrar, usa-se o motor local.
"""
import json
import math
import re
import unicodedata

from backend.models.lugar import Lugar
from backend.services.gemini_service import GeminiService
from backend.services.integracoes.pontos_interesse_service import (
    TIPO_PARA_INTERESSE,
    TIPOS_ROTULO,
    PontosInteresseService,
)
from backend.utils.geo import distancia_km
from backend.utils.validadores import hora_para_minutos, minutos_para_hora

RITMOS = {"leve": 2, "moderado": 3, "intenso": 4}
RAIO_CATALOGO_KM = 80
RAIO_PONTOS_KM = 6

# Estimativas de planejamento (editáveis pelo usuário), não informações do estabelecimento.
DURACAO_ESTIMADA = {
    "praia": 180, "natureza": 180, "aventura": 180, "museus": 120, "cultura": 120, "gastronomia": 90,
    "restaurante": 90, "cafe": 45, "museu": 120, "mirante": 60, "atracao": 90, "historico": 60,
    "parque": 90,
}
CATEGORIA_ATIVIDADE = {
    "praia": "natureza", "natureza": "natureza", "aventura": "experiencia", "museus": "cultura",
    "cultura": "cultura", "gastronomia": "restaurante",
}

DIAS_OSM = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"[̀-ͯ]", "", texto)).strip()


def interpretar_funcionamento(valor):
    """Interpreta formatos simples de opening_hours ("Tu-Su 10:00-18:00; Mo off").

    Devolve {indice_dia_semana: [(inicio_min, fim_min), ...]} ou None se o formato
    não for reconhecido (nesse caso nada é presumido).
    """
    if not valor:
        return None
    if valor.strip() == "24/7":
        return {d: [(0, 24 * 60)] for d in range(7)}
    resultado = {}
    for parte in valor.split(";"):
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"^([A-Z][a-z](?:\s*-\s*[A-Z][a-z])?(?:\s*,\s*[A-Z][a-z](?:\s*-\s*[A-Z][a-z])?)*)\s+(.+)$", parte)
        if not m:
            return None
        dias = set()
        for bloco in m.group(1).split(","):
            extremos = [b.strip() for b in bloco.split("-")]
            if any(e not in DIAS_OSM for e in extremos):
                return None
            inicio, fim = DIAS_OSM.index(extremos[0]), DIAS_OSM.index(extremos[-1])
            atual = inicio
            while True:
                dias.add(atual)
                if atual == fim:
                    break
                atual = (atual + 1) % 7
        horarios = m.group(2).strip()
        if horarios == "off":
            for d in dias:
                resultado[d] = []
            continue
        faixas = []
        for faixa in horarios.split(","):
            h = re.match(r"^(\d{2}:\d{2})-(\d{2}:\d{2})$", faixa.strip())
            if not h:
                return None
            faixas.append((hora_para_minutos(h.group(1)), hora_para_minutos(h.group(2)) if h.group(2) != "24:00" else 1440))
        for d in dias:
            resultado[d] = faixas
    return resultado or None


class RoteiroInteligenteService:
    def __init__(self, servico_pontos=None, servico_ia=None):
        self.servico_pontos = servico_pontos or PontosInteresseService()
        self.servico_ia = servico_ia or GeminiService()

    # ------------------------------------------------------------------
    def executar(self, viagem, parametros):
        candidatos, aviso = self._candidatos(viagem, parametros)
        plano, origem, observacoes = None, "local", None
        if self.servico_ia.configurado and candidatos:
            plano, observacoes = self._planejar_com_ia(viagem, parametros, candidatos)
            if plano:
                origem = "gemini"
        if not plano:
            plano = self._planejar_localmente(viagem, parametros, candidatos)
            observacoes = self._observacoes_locais(viagem, candidatos, aviso)
        self._conferir_funcionamento(viagem, plano)
        return {"atividades": plano, "origem": origem, "observacoes": observacoes, "total_candidatos": len(candidatos)}

    # ------------------------------------------------------------------
    def _centro(self, viagem):
        if viagem.latitude is not None and viagem.longitude is not None:
            return viagem.latitude, viagem.longitude
        if viagem.lugar is not None:
            return viagem.lugar.latitude, viagem.lugar.longitude
        return None

    def _candidatos(self, viagem, parametros):
        interesses = set(parametros.get("interesses") or [])
        orcamento = parametros.get("orcamento") or 2
        centro = self._centro(viagem)
        candidatos, aviso = [], None
        destino_normalizado = _normalizar(viagem.destino)

        for lugar in Lugar.listar_todos():
            if centro:
                distancia = distancia_km(centro, (lugar.latitude, lugar.longitude))
                if distancia > RAIO_CATALOGO_KM:
                    continue
            elif _normalizar(lugar.cidade) not in destino_normalizado:
                continue
            pontos = 2.0 + (lugar.nota - 4.0) * 2
            pontos += 3 if lugar.categoria in interesses else 0
            pontos += 1 if abs(lugar.faixa_preco - orcamento) <= 1 else -1.5
            if viagem.lugar_id == lugar.id:
                pontos += 10  # o destino principal escolhido sempre entra
            candidatos.append({
                "chave": f"l:{lugar.id}", "titulo": lugar.nome, "interesse": lugar.categoria,
                "categoria": CATEGORIA_ATIVIDADE.get(lugar.categoria, "atracao"),
                "refeicao": lugar.categoria == "gastronomia",
                "latitude": lugar.latitude, "longitude": lugar.longitude, "descricao": lugar.descricao,
                "lugar_id": lugar.id, "ponto_id": None, "endereco": f"{lugar.cidade}, {lugar.estado}",
                "funcionamento": None, "fonte": "catalogo", "pontos": pontos, "nota": lugar.nota,
                "duracao": DURACAO_ESTIMADA.get(lugar.categoria, 90),
            })

        if centro:
            resultado = self.servico_pontos.proximos(
                centro[0], centro[1], raio_km=RAIO_PONTOS_KM, limite=120,
                buscar_externo=bool(parametros.get("buscar_externo", True)),
            )
            aviso = resultado.get("aviso")
            nomes = {_normalizar(c["titulo"]) for c in candidatos}
            for ponto in resultado["pontos"]:
                if _normalizar(ponto["nome"]) in nomes:
                    continue
                nomes.add(_normalizar(ponto["nome"]))
                interesse = TIPO_PARA_INTERESSE.get(ponto["tipo"], "cultura")
                refeicao = ponto["tipo"] in ("restaurante", "cafe")
                pontos = 1.0 + (2.5 if interesse in interesses else 0) - min(2, ponto["distancia_km"] / 3)
                candidatos.append({
                    "chave": f"p:{ponto['id']}", "titulo": ponto["nome"], "interesse": interesse,
                    "categoria": "restaurante" if refeicao else ("natureza" if interesse in ("natureza", "praia") else "atracao"),
                    "refeicao": refeicao, "latitude": ponto["latitude"], "longitude": ponto["longitude"],
                    "descricao": f"{TIPOS_ROTULO.get(ponto['tipo'], 'Ponto de interesse')} · dados do OpenStreetMap",
                    "lugar_id": None, "ponto_id": ponto["id"], "endereco": ponto.get("endereco"),
                    "funcionamento": ponto.get("funcionamento"), "fonte": "openstreetmap", "pontos": pontos,
                    "nota": None, "duracao": DURACAO_ESTIMADA.get(ponto["tipo"], 90),
                })
        candidatos.sort(key=lambda c: c["pontos"], reverse=True)
        return candidatos, aviso

    # ------------------------------------------------------------------
    @staticmethod
    def _ordenar_por_proximidade(itens, inicio):
        """Vizinho mais próximo a partir do centro: reduz deslocamentos desnecessários."""
        restantes, rota, atual = list(itens), [], inicio
        while restantes:
            if atual is None:
                proximo = restantes[0]
            else:
                proximo = min(restantes, key=lambda c: distancia_km(atual, (c["latitude"], c["longitude"])))
            rota.append(proximo)
            restantes.remove(proximo)
            atual = (proximo["latitude"], proximo["longitude"])
        return rota

    def _planejar_localmente(self, viagem, parametros, candidatos):
        dias = viagem.duracao_dias
        por_dia = RITMOS.get(parametros.get("ritmo"), 3)
        incluir_refeicoes = parametros.get("incluir_refeicoes", True)
        passeios = [c for c in candidatos if not c["refeicao"]]
        refeicoes = [c for c in candidatos if c["refeicao"]]
        # Restaurantes do catálogo também podem ser a "atividade" principal de quem ama gastronomia
        if "gastronomia" in (parametros.get("interesses") or []) and not incluir_refeicoes:
            passeios += refeicoes

        capacidades = [max(1, por_dia - 1) if (d == dias and dias > 1) else por_dia for d in range(1, dias + 1)]
        escolhidos = passeios[: sum(capacidades)]
        rota = self._ordenar_por_proximidade(escolhidos, self._centro(viagem))

        plano, cursor = [], 0
        usados_refeicao = set()
        for dia, capacidade in enumerate(capacidades, start=1):
            do_dia = rota[cursor: cursor + capacidade]
            cursor += capacidade
            plano.extend(self._agenda_do_dia(viagem, dia, do_dia, refeicoes if incluir_refeicoes else [],
                                             usados_refeicao, dia == dias and dias > 1))
        return plano

    def _agenda_do_dia(self, viagem, dia, atividades, refeicoes, usados, ultimo_dia):
        itens, minuto = [], 9 * 60
        centro_dia = None
        if atividades:
            centro_dia = (sum(a["latitude"] for a in atividades) / len(atividades),
                          sum(a["longitude"] for a in atividades) / len(atividades))

        def refeicao_proxima():
            livres = [r for r in refeicoes if r["chave"] not in usados]
            if not livres or centro_dia is None:
                return None
            escolha = min(livres, key=lambda r: distancia_km(centro_dia, (r["latitude"], r["longitude"])) - r["pontos"])
            usados.add(escolha["chave"])
            return escolha

        metade = math.ceil(len(atividades) / 2)
        for indice, atividade in enumerate(atividades):
            if indice == metade and refeicoes:
                almoco = refeicao_proxima()
                if almoco:
                    minuto = max(minuto, 12 * 60)
                    itens.append(self._item(dia, almoco, minuto, 75, "Almoço"))
                    minuto += 75 + 20
            itens.append(self._item(dia, atividade, minuto, atividade["duracao"]))
            minuto += atividade["duracao"] + 30  # margem para deslocamento
        if refeicoes and atividades:
            jantar = refeicao_proxima()
            if jantar:
                itens.append(self._item(dia, jantar, max(minuto, 19 * 60 + 30), 90, "Jantar"))
        if not itens:
            itens.append({
                "dia": dia, "titulo": f"Tempo livre em {viagem.destino}", "categoria": "descanso",
                "descricao": "Não encontramos mais opções confirmadas para este dia. Adicione atividades "
                             "manualmente ou peça sugestões ao grupo.",
                "horario": None, "horario_sugerido": False, "duracao_min": None, "fonte": "sugestao",
            })
        if ultimo_dia:
            itens.append({
                "dia": dia, "titulo": "Retorno", "categoria": "transporte", "horario": None,
                "horario_sugerido": False, "duracao_min": None, "fonte": "sugestao",
                "descricao": "Reserve tempo para o check-out e o deslocamento de volta.",
            })
        return itens

    @staticmethod
    def _item(dia, candidato, minuto, duracao, prefixo=None):
        return {
            "dia": dia,
            "titulo": f"{prefixo}: {candidato['titulo']}" if prefixo else candidato["titulo"],
            "descricao": candidato["descricao"],
            "categoria": "restaurante" if prefixo else candidato["categoria"],
            "horario": minutos_para_hora(minuto),
            "horario_sugerido": True,
            "duracao_min": duracao,
            "lugar_id": candidato["lugar_id"],
            "ponto_id": candidato["ponto_id"],
            "endereco": candidato["endereco"],
            "latitude": candidato["latitude"],
            "longitude": candidato["longitude"],
            "funcionamento": candidato["funcionamento"],
            "fonte": candidato["fonte"],
        }

    # ------------------------------------------------------------------
    def _conferir_funcionamento(self, viagem, plano):
        """Ajusta/alerta com base no opening_hours do OSM (único dado de horário confiável)."""
        for item in plano:
            faixas = interpretar_funcionamento(item.get("funcionamento"))
            if not faixas or not item.get("horario"):
                continue
            dia_semana = viagem.data_do_dia(item["dia"]).weekday()
            if dia_semana not in faixas:
                continue
            abertos = faixas[dia_semana]
            inicio = hora_para_minutos(item["horario"])
            if not abertos:
                item["descricao"] = (item.get("descricao") or "") + \
                    " ⚠ Segundo o OpenStreetMap, fecha neste dia da semana — confirme antes de ir."
                continue
            if not any(a <= inicio < b for a, b in abertos):
                posterior = [a for a, b in abertos if a > inicio]
                if posterior:
                    item["horario"] = minutos_para_hora(posterior[0])
                    item["descricao"] = (item.get("descricao") or "") + \
                        " Horário ajustado à abertura informada no OpenStreetMap."
                else:
                    item["descricao"] = (item.get("descricao") or "") + \
                        " ⚠ Pode estar fechado neste horário (OpenStreetMap) — confirme."

    def _observacoes_locais(self, viagem, candidatos, aviso):
        partes = [f"Roteiro montado com {len(candidatos)} opções reais perto de {viagem.destino} "
                  "(catálogo Viajaí e OpenStreetMap), agrupadas por proximidade para reduzir deslocamentos."]
        partes.append("Horários são sugestões de distribuição do dia: confirme funcionamento e reservas.")
        if aviso:
            partes.append(f"Mapa de estabelecimentos indisponível agora ({aviso}).")
        return " ".join(partes)

    # ------------------------------------------------------------------
    def _planejar_com_ia(self, viagem, parametros, candidatos):
        lista = candidatos[:60]
        por_chave = {c["chave"]: c for c in lista}
        resumo = [
            {"chave": c["chave"], "nome": c["titulo"], "tipo": c["interesse"], "refeicao": c["refeicao"],
             "lat": round(c["latitude"], 4), "lon": round(c["longitude"], 4),
             "funcionamento": c["funcionamento"], "nota": c["nota"]}
            for c in lista
        ]
        prompt = (
            f"Monte um roteiro para '{viagem.destino}' com {viagem.duracao_dias} dia(s), começando em "
            f"{viagem.data_ida.isoformat()}, para {viagem.viajantes} viajante(s).\n"
            f"Interesses: {', '.join(parametros.get('interesses') or []) or 'variados'}. "
            f"Orçamento (1 a 4): {parametros.get('orcamento') or 2}. Ritmo: {parametros.get('ritmo') or 'moderado'} "
            f"({RITMOS.get(parametros.get('ritmo'), 3)} atividades por dia). "
            f"Incluir almoço/jantar: {'sim' if parametros.get('incluir_refeicoes', True) else 'não'}.\n"
            f"Observações do viajante: {parametros.get('observacoes') or 'nenhuma'}.\n\n"
            "Use SOMENTE itens desta lista (campo 'chave'), agrupando por dia os que estão próximos "
            "(lat/lon) para evitar deslocamentos. Respeite 'funcionamento' quando informado. "
            "Não invente lugares, preços ou horários de funcionamento.\n"
            f"Candidatos: {json.dumps(resumo, ensure_ascii=False)}\n\n"
            'Responda apenas JSON: {"observacoes": "texto curto", "dias": [{"dia": 1, "atividades": '
            '[{"chave": "l:1", "horario": "09:00", "duracao_min": 120, "dica": "texto curto opcional"}]}]}'
        )
        resposta = self.servico_ia.gerar_json(prompt)
        if not isinstance(resposta, dict):
            return None, None
        plano = []
        for dia_info in resposta.get("dias") or []:
            try:
                dia = int(dia_info.get("dia"))
            except (TypeError, ValueError):
                continue
            if not 1 <= dia <= viagem.duracao_dias:
                continue
            for atividade in dia_info.get("atividades") or []:
                candidato = por_chave.get(str(atividade.get("chave")))
                if candidato is None:
                    continue  # item inventado/desconhecido: descartado
                horario = str(atividade.get("horario") or "")[:5]
                minuto = hora_para_minutos(horario) if re.match(r"^([01]\d|2[0-3]):[0-5]\d$", horario) else 9 * 60
                try:
                    duracao = max(15, min(600, int(atividade.get("duracao_min") or candidato["duracao"])))
                except (TypeError, ValueError):
                    duracao = candidato["duracao"]
                item = self._item(dia, candidato, minuto, duracao)
                dica = str(atividade.get("dica") or "").strip()[:300]
                if dica:
                    item["descricao"] = f"{candidato['descricao']} Dica do Vai: {dica}"
                plano.append(item)
        if not plano:
            return None, None
        observacoes = str(resposta.get("observacoes") or "").strip()[:600]
        return plano, (observacoes + " " if observacoes else "") + \
            "Sugestões geradas pelo Vai (Gemini) a partir de lugares reais; horários são sugestões."
