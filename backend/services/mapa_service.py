"""Casos de uso do Mapa Interativo (feature 4).

    ConfiguracaoMapaService · LugaresNoMapaService · MapaViagemService · ProximidadesLugarService

Distâncias são calculadas em linha reta (Haversine) e rotuladas como tal: não
inventamos rotas nem tempos de deslocamento.
"""
from backend.config import Config
from backend.models.lugar import Lugar
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.services.integracoes.pontos_interesse_service import TIPOS_ROTULO, PontosInteresseService
from backend.utils.erros import NaoEncontrado
from backend.utils.geo import distancia_km


class ConfiguracaoMapaService:
    def executar(self):
        return {
            "tile_url": Config.MAPA_TILE_URL,
            "atribuicao": Config.MAPA_TILE_ATRIBUICAO,
            "integracoes_externas": Config.INTEGRACOES_EXTERNAS,
            "aviso_distancias": "Distâncias em linha reta — o trajeto real pode ser maior.",
            "tipos_pontos": TIPOS_ROTULO,
        }


class LugaresNoMapaService:
    def executar(self):
        return {"lugares": [
            {"id": l.id, "nome": l.nome, "categoria": l.categoria, "tipo": l.tipo, "local": f"{l.cidade}, {l.estado}",
             "latitude": l.latitude, "longitude": l.longitude, "nota": round(l.nota, 1), "preco_simbolo": l.preco_simbolo,
             "foto": l.foto_principal_dict(), "imagem": l.imagem}
            for l in Lugar.listar_todos()
        ]}


class MapaViagemService:
    def __init__(self, autorizacao=None):
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, viagem_id, usuario):
        viagem = self.autorizacao.executar(viagem_id, usuario, "leitura")
        pontos = []
        if viagem.latitude is not None:
            pontos.append({"chave": "destino", "tipo": "destino", "titulo": viagem.destino,
                           "latitude": viagem.latitude, "longitude": viagem.longitude, "dia": None})
        roteiro = viagem.roteiro_ativo
        dias = {}
        if roteiro:
            for atividade in roteiro.atividades:
                if atividade.latitude is None:
                    continue
                ponto = {"chave": f"a{atividade.id}", "tipo": "atividade", "id": atividade.id,
                         "titulo": atividade.titulo, "categoria": atividade.categoria, "dia": atividade.dia,
                         "ordem": atividade.ordem, "horario": atividade.horario, "latitude": atividade.latitude,
                         "longitude": atividade.longitude, "lugar_id": atividade.lugar_id,
                         "endereco": atividade.endereco, "funcionamento": atividade.funcionamento}
                pontos.append(ponto)
                dias.setdefault(atividade.dia, []).append(ponto)
        for compromisso in viagem.compromissos:
            if compromisso.latitude is not None:
                pontos.append({"chave": f"c{compromisso.id}", "tipo": "compromisso", "id": compromisso.id,
                               "titulo": compromisso.titulo, "dia": (compromisso.inicio.date() - viagem.data_ida).days + 1,
                               "horario": compromisso.inicio.strftime("%H:%M"), "latitude": compromisso.latitude,
                               "longitude": compromisso.longitude, "endereco": compromisso.local})
        trajetos = []
        for dia, itens in sorted(dias.items()):
            itens.sort(key=lambda p: (p["horario"] or "99:99", p["ordem"]))
            trechos = [
                {"de": a["titulo"], "para": b["titulo"],
                 "distancia_km": distancia_km((a["latitude"], a["longitude"]), (b["latitude"], b["longitude"]))}
                for a, b in zip(itens, itens[1:])
            ]
            trajetos.append({"dia": dia, "pontos": [p["chave"] for p in itens], "trechos": trechos,
                             "total_km": round(sum(t["distancia_km"] for t in trechos), 1)})
        return {"viagem": {"id": viagem.id, "destino": viagem.destino, "latitude": viagem.latitude,
                           "longitude": viagem.longitude},
                "pontos": pontos, "trajetos": trajetos, "sem_localizacao": viagem.latitude is None and not pontos}


class ProximidadesLugarService:
    def __init__(self, servico_pontos=None):
        self.servico_pontos = servico_pontos or PontosInteresseService()

    def executar(self, lugar_id, raio_km=5, tipos=None):
        lugar = Lugar.buscar_por_id(lugar_id)
        if lugar is None:
            raise NaoEncontrado("Lugar não encontrado.")
        raio_km = max(1, min(15, raio_km or 5))
        catalogo = []
        for outro in Lugar.listar_todos():
            if outro.id == lugar.id:
                continue
            distancia = distancia_km((lugar.latitude, lugar.longitude), (outro.latitude, outro.longitude))
            if distancia <= 60:
                catalogo.append({"id": outro.id, "nome": outro.nome, "categoria": outro.categoria,
                                 "latitude": outro.latitude, "longitude": outro.longitude, "distancia_km": distancia})
        catalogo.sort(key=lambda i: i["distancia_km"])
        resultado = self.servico_pontos.proximos(lugar.latitude, lugar.longitude, raio_km=raio_km, tipos=tipos)
        return {"lugar": {"id": lugar.id, "nome": lugar.nome, "latitude": lugar.latitude, "longitude": lugar.longitude},
                "catalogo": catalogo, "pontos": resultado["pontos"], "aviso": resultado["aviso"],
                "raio_km": raio_km, "fonte_pontos": "OpenStreetMap (Overpass API)"}
