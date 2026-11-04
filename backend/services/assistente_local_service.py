"""Caso de uso: responder ao usuário sem depender de serviço externo.

Motor de reserva do assistente Vai. É usado quando a GEMINI_API_KEY não está
configurada ou quando a API externa falha, para que o chat nunca fique mudo.
"""
import random
import re
import unicodedata


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return re.sub(r"[\u0300-\u036f]", "", texto)


def _brl(valor):
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


class AssistenteLocalService:
    def executar(self, pergunta, contexto):
        texto = _normalizar(pergunta)
        nome = contexto.get("nome", "viajante")
        lugares = contexto.get("lugares", [])
        interesses = contexto.get("interesses", [])
        cidade = contexto.get("cidade") or "sua cidade"
        orcamento = contexto.get("orcamento_rotulo", "moderado")

        def top(n=3):
            return lugares[:n]

        viagens = contexto.get("viagens") or []
        viagem = next((v for v in viagens if v.get("foco")), viagens[0] if viagens else None)
        resposta_viagem = self._responder_sobre_viagem(texto, viagem, contexto)
        if resposta_viagem:
            return resposta_viagem

        def linha(lugar):
            return (
                f"• {lugar['nome']} — {lugar['local']} · nota {lugar['nota']} · "
                f"{lugar['preco_simbolo']} · {lugar['match']}% de match"
            )

        if any(p in texto for p in ("criar viagem", "planejar", "nova viagem", "quero ir", "organizar uma viagem")):
            return (
                "Vamos planejar! Toque em 'Criar viagem' abaixo: informe destino, datas e quantas pessoas vão. "
                "Depois eu monto o roteiro por dia, e você acompanha gastos, agenda e checklist da mala."
            )

        if any(p in texto for p in ("roteiro", "itinerario", "programacao", "3 dias", "fim de semana")):
            escolhidos = top(3)
            if not escolhidos:
                return "Escolha alguns interesses no seu perfil que eu monto um roteiro sob medida."
            partes = [f"Um roteiro de 3 dias pensado no seu perfil, {nome}:"]
            for i, lugar in enumerate(escolhidos, start=1):
                partes.append(
                    f"\nDia {i} — {lugar['nome']} ({lugar['local']})\n"
                    f"{lugar['descricao']} Faixa de preço {lugar['preco_simbolo']}."
                )
            partes.append("\nQuer que eu ajuste para mais dias ou outro orçamento?")
            return "\n".join(partes)

        if any(p in texto for p in ("melhor epoca", "epoca", "quando ir", "clima", "temporada")):
            escolhidos = top(3)
            if not escolhidos:
                return "Me diga um destino que eu te conto a melhor época para ir."
            partes = ["Melhores épocas para os destinos do seu perfil:"]
            for lugar in escolhidos:
                partes.append(
                    f"• {lugar['nome']}: {lugar.get('melhor_epoca') or 'boa o ano todo, com menos chuva no inverno'}."
                )
            return "\n".join(partes)

        if any(p in texto for p in ("preco", "custo", "quanto custa", "orcamento", "barato", "gastar")):
            escolhidos = top(4)
            partes = [f"Seu orçamento está em '{orcamento}'. Nessa faixa eu recomendo:"]
            partes += [linha(lugar) for lugar in escolhidos] or ["Ainda não tenho destinos salvos no seu perfil."]
            partes.append("Posso filtrar só as opções mais econômicas, se preferir.")
            return "\n".join(partes)

        if any(p in texto for p in ("praia", "mar", "litoral")):
            praias = [l for l in lugares if l["categoria"] == "praia"][:3]
            if praias:
                return "Praias que combinam com você:\n" + "\n".join(linha(l) for l in praias)

        if any(p in texto for p in ("comer", "restaurante", "comida", "gastronomia", "jantar")):
            comidas = [l for l in lugares if l["categoria"] == "gastronomia"][:3]
            if comidas:
                return "Para comer bem:\n" + "\n".join(linha(l) for l in comidas)

        if any(p in texto for p in ("perto", "proximo", "aqui", "perto de mim")):
            proximos = sorted(lugares, key=lambda l: l.get("distancia_km", 9999))[:3]
            if proximos:
                return (
                    f"Perto de {cidade}:\n"
                    + "\n".join(f"{linha(l)} · {l.get('distancia_km', 0)} km" for l in proximos)
                )

        if any(p in texto for p in ("oi", "ola", "bom dia", "boa tarde", "boa noite", "tudo bem")):
            return (
                f"Oi, {nome}! Posso sugerir roteiros, melhores épocas, preços e lugares "
                "que combinam com os seus interesses. O que você quer saber?"
            )

        if any(p in texto for p in ("obrigad", "valeu", "brigad")):
            return random.choice(
                ["Por nada! Boa viagem ✈️", "Disponha! Qualquer dúvida é só chamar."]
            )

        sugestoes = top(3)
        base = (
            f"{nome}, com base nos seus interesses ({', '.join(interesses) or 'ainda não definidos'}) "
            f"e no orçamento {orcamento}, estas são as melhores opções agora:"
        )
        if not sugestoes:
            return (
                "Ainda não tenho destinos suficientes para responder isso. "
                "Atualize seus interesses no perfil e me pergunte de novo."
            )
        return base + "\n" + "\n".join(linha(l) for l in sugestoes) + (
            "\n\nPosso montar um roteiro, comparar preços ou indicar a melhor época — é só pedir."
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _responder_sobre_viagem(texto, viagem, contexto):
        """Respostas que usam os dados da viagem — só existem se o usuário autorizou."""
        pede_viagem = any(p in texto for p in (
            "minha viagem", "minhas viagens", "proxima viagem", "gasto", "orcamento da viagem", "saldo",
            "agenda", "compromisso", "calendario", "conflito", "mala", "checklist", "levar", "falta"))
        if not pede_viagem:
            return None
        if viagem is None:
            permissoes = contexto.get("permissoes") or {}
            if not permissoes.get("usar_viagens"):
                return ("Para falar das suas viagens eu preciso da sua autorização. Ative 'Viagens planejadas' "
                        "nas permissões do Vai (ícone 🔒 no topo do chat) ou escolha uma viagem no seletor.")
            return "Você ainda não tem viagens planejadas. Que tal criar a primeira? É só tocar em 'Viagens'."

        nome = f"'{viagem['titulo']}' ({viagem['destino']})"
        if any(p in texto for p in ("gasto", "orcamento", "saldo", "dinheiro")):
            financas = viagem.get("financas")
            if not financas:
                return ("Para analisar gastos eu preciso da permissão 'Orçamentos e gastos' "
                        "(ícone 🔒 no topo do chat) — ou selecione esta viagem no seletor do chat.")
            linhas = [f"Finanças de {nome}:"]
            if financas.get("orcamento") is not None:
                linhas.append(f"• Orçamento: {_brl(financas['orcamento'])} · gasto: {_brl(financas['gasto'])} "
                              f"· saldo: {_brl(financas['saldo'])}")
            else:
                linhas.append(f"• Gasto até agora: {_brl(financas['gasto'])} (orçamento ainda não definido)")
            linhas.append(f"• Por pessoa: {_brl(financas['gasto_por_pessoa'])}")
            for categoria, valor in (financas.get("por_categoria") or {}).items():
                linhas.append(f"• {categoria}: {_brl(valor)}")
            linhas += [f"⚠ {a}" for a in financas.get("alertas", [])]
            return "\n".join(linhas)

        if any(p in texto for p in ("agenda", "compromisso", "calendario", "conflito")):
            agenda = viagem.get("agenda") or []
            if not agenda:
                return f"A agenda de {nome} ainda está vazia. Adicione reservas e passeios na aba Agenda."
            linhas = [f"Próximos compromissos de {nome}:"]
            linhas += [f"• {e['inicio'].replace('T', ' ')} — {e['titulo']}{' ⚠ conflito' if e['conflito'] else ''}"
                       for e in agenda[:6]]
            if viagem.get("conflitos"):
                linhas.append(f"Há {viagem['conflitos']} conflito(s) de horário — vale reorganizar.")
            return "\n".join(linhas)

        if any(p in texto for p in ("mala", "checklist", "levar", "falta")):
            checklist = viagem.get("checklist")
            if not checklist:
                return f"Ainda não há checklist para {nome}. Na aba Checklist eu gero sugestões para a viagem."
            linhas = [f"Checklist de {nome}: {checklist['concluidos']} de {checklist['total']} itens prontos."]
            if checklist["pendentes"]:
                linhas.append("Ainda falta: " + ", ".join(checklist["pendentes"][:6]) + ".")
            return "\n".join(linhas)

        dias = viagem.get("dias_para_partir")
        quando = (f"faltam {dias} dias" if dias and dias > 0 else "é hoje!" if dias == 0 else "já começou")
        linhas = [f"Sua viagem {nome}: {viagem['data_ida']} a {viagem['data_volta']} — {quando}."]
        if viagem.get("roteiro"):
            linhas.append(f"O roteiro principal tem {len(viagem['roteiro'])} atividades. Primeiro dia: " +
                          ", ".join(a["titulo"] for a in viagem["roteiro"] if a["dia"] == 1)[:200] + ".")
        else:
            linhas.append("Ainda não há roteiro — posso gerar um com lugares reais do destino.")
        return "\n".join(linhas)
