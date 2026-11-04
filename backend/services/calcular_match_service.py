"""Caso de uso: calcular a compatibilidade (match %) entre um lugar e o perfil do usuário.

Regra de negócio isolada num Service próprio porque é reutilizada pela listagem,
pela busca e pelas recomendações.
"""
from backend.utils.geo import coordenadas_da_cidade, distancia_km


class CalcularMatchService:
    BASE = 44

    def executar(self, lugar, preferencia, distancia=None):
        if preferencia is None:
            return min(99, int(round(self.BASE + 12 + (lugar.nota - 4.0) * 20)))

        pontos = self.BASE
        interesses = set(preferencia.slugs_interesses)

        # 1) alinhamento com os interesses escolhidos
        if lugar.categoria in interesses:
            pontos += 24
        elif interesses:
            pontos -= 6

        # 2) qualidade percebida (nota)
        pontos += (lugar.nota - 4.0) * 12

        # 3) aderência ao orçamento
        diferenca = abs(lugar.faixa_preco - preferencia.orcamento)
        pontos += {0: 9, 1: 4}.get(diferenca, -7)

        # 4) proximidade da cidade do usuário
        if distancia is None:
            distancia = self.distancia_para(lugar, preferencia)
        if distancia <= 60:
            pontos += 10
        elif distancia <= 300:
            pontos += 6
        elif distancia <= 1200:
            pontos += 3

        # 5) popularidade entre os usuários do app
        pontos += min(5, getattr(lugar, "popularidade", 0))

        return int(max(35, min(99, round(pontos))))

    @staticmethod
    def distancia_para(lugar, preferencia):
        if preferencia is None:
            return 0.0
        origem = coordenadas_da_cidade(preferencia.cidade, preferencia.estado)
        return distancia_km(origem, (lugar.latitude, lugar.longitude))
