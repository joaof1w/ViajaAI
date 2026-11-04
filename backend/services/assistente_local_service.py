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

        def linha(lugar):
            return (
                f"• {lugar['nome']} — {lugar['local']} · nota {lugar['nota']} · "
                f"{lugar['preco_simbolo']} · {lugar['match']}% de match"
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
