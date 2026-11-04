"""Testes de integração das 12 funcionalidades da expansão (API completa via Flask test client).

Execute na raiz do projeto:
    python -m unittest backend.tests.test_funcionalidades -v
As integrações externas ficam DESLIGADAS: onde há serviço externo (Wikimedia, Overpass,
Gemini), os testes usam respostas simuladas e isso está indicado no nome do teste.
"""
import io
import json
import os
import unittest
from datetime import date, timedelta

from backend.tests.apoio import CasoComApp, imagem_png

HOJE = date.today()


def d(dias):
    return (HOJE + timedelta(days=dias)).isoformat()


class TestCompatibilidade(CasoComApp):
    """Funcionalidades antigas continuam funcionando."""

    def test_fluxo_original(self):
        token, _ = self.criar_usuario()
        self.assertEqual(self.requisitar("GET", "/api/saude")[0], 200)
        status, perfil = self.requisitar("GET", "/api/usuarios/eu", token)
        self.assertEqual(status, 200)
        self.assertTrue(perfil["possui_preferencias"])
        status, dados = self.requisitar("GET", "/api/lugares/recomendacoes", token)
        self.assertEqual(status, 200)
        self.assertTrue(dados["lugares"])
        self.assertIn("foto", dados["lugares"][0])  # novo campo, sem quebrar os antigos
        self.assertIn("match", dados["lugares"][0])
        lugar_id = dados["lugares"][0]["id"]
        self.assertEqual(self.requisitar("POST", "/api/favoritos", token, json={"lugar_id": lugar_id})[0], 201)
        status, salvos = self.requisitar("GET", "/api/favoritos", token)
        self.assertEqual(salvos["total"], 1)
        status, busca = self.requisitar("GET", "/api/lugares/busca?q=praia&ordenar=match", token)
        self.assertEqual(status, 200)
        status, chat = self.requisitar("POST", "/api/chat", token, json={"texto": "me sugere um roteiro"})
        self.assertEqual(status, 201)
        self.assertIn("Dia 1", chat["resposta"]["texto"])
        self.assertEqual(self.requisitar("GET", "/api/relatorios/destinos")[0], 200)
        self.assertEqual(self.requisitar("GET", "/api/viagens")[0], 401)  # rota privada
        self.assertEqual(self.requisitar("POST", "/api/auth/logout", token)[0], 200)
        self.assertEqual(self.requisitar("GET", "/api/usuarios/eu", token)[0], 401)

    def test_cabecalhos_de_seguranca(self):
        resposta = self.cliente.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("default-src 'self'", resposta.headers["Content-Security-Policy"])
        self.assertEqual(resposta.headers["X-Frame-Options"], "DENY")
        self.assertEqual(self.cliente.get("/viagens").status_code, 200)  # páginas novas servidas


class TestPlanejador(CasoComApp):
    def test_crud_e_status(self):
        token, _ = self.criar_usuario()
        rio = self.lugar_por_nome("Museu do Amanhã")
        status, criada = self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Rio de Janeiro, RJ", "lugar_id": rio, "data_ida": d(10), "data_volta": d(13),
            "viajantes": 2, "orcamento": "3.500,00", "tipo": "cultural", "observacoes": "Sem pressa"})
        self.assertEqual(status, 201, criada)
        viagem = criada["viagem"]
        self.assertEqual(viagem["status"], "futura")
        self.assertEqual(viagem["duracao_dias"], 4)
        self.assertEqual(viagem["orcamento"], 3500.0)
        self.assertIsNotNone(viagem["latitude"])  # coordenadas do lugar do catálogo
        self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Ouro Preto, MG", "data_ida": d(-2), "data_volta": d(2)})
        self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Bonito, MS", "data_ida": d(-30), "data_volta": d(-25)})
        status, lista = self.requisitar("GET", "/api/viagens", token)
        self.assertEqual(lista["contagem"], {"futura": 1, "em_andamento": 1, "concluida": 1})
        self.assertEqual(lista["viagens"][0]["status"], "em_andamento")
        status, so = self.requisitar("GET", "/api/viagens?status=concluida", token)
        self.assertEqual([v["destino"] for v in so["viagens"]], ["Bonito, MS"])

        status, editada = self.requisitar("PUT", f"/api/viagens/{viagem['id']}", token, json={"viajantes": 3})
        self.assertEqual(editada["viagem"]["viajantes"], 3)
        self.assertEqual(editada["viagem"]["destino"], "Rio de Janeiro, RJ")  # edição parcial
        status, detalhe = self.requisitar("GET", f"/api/viagens/{viagem['id']}", token)
        self.assertEqual(status, 200)
        self.assertTrue(detalhe["permissoes"]["gerenciar"])
        self.assertEqual(self.requisitar("DELETE", f"/api/viagens/{viagem['id']}", token)[0], 200)
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{viagem['id']}", token)[0], 404)

    def test_validacoes(self):
        token, _ = self.criar_usuario(email="val@email.com")
        casos = [
            ({"destino": "Natal", "data_ida": d(5), "data_volta": d(1)}, "data_volta"),
            ({"destino": "", "data_ida": d(1), "data_volta": d(2)}, "destino"),
            ({"destino": "Natal", "data_ida": "31/12/2026", "data_volta": d(2)}, "data_ida"),
            ({"destino": "Natal", "data_ida": d(1), "data_volta": d(2), "viajantes": 0}, "viajantes"),
            ({"destino": "Natal", "data_ida": d(1), "data_volta": d(2), "orcamento": "-10"}, "orcamento"),
            ({"destino": "Natal", "data_ida": d(1), "data_volta": d(200)}, "data_volta"),
            ({"destino": "Natal", "data_ida": d(1), "data_volta": d(2), "lugar_id": 9999}, "lugar_id"),
            ({"destino": "Natal", "data_ida": d(1), "data_volta": d(2), "tipo": "hackear"}, "tipo"),
        ]
        for corpo, campo in casos:
            status, erro = self.requisitar("POST", "/api/viagens", token, json=corpo)
            self.assertEqual(status, 422, (corpo, erro))
            self.assertEqual(erro.get("campo"), campo)


class TestGrupoEPermissoes(CasoComApp):
    def test_convites_papeis_e_isolamento(self):
        ana, _ = self.criar_usuario()
        bia, bia_id = self.criar_usuario(nome="Bia Souza", email="bia@email.com")
        caio, _ = self.criar_usuario(nome="Caio Melo", email="caio@email.com")
        _, viagem = self.requisitar("POST", "/api/viagens", ana, json={
            "destino": "Salvador, BA", "data_ida": d(20), "data_volta": d(23)})
        vid = viagem["viagem"]["id"]

        # Sem convite: nada vaza (404 em vez de 403)
        for rota in ("", "/financas", "/checklist", "/calendario", "/roteiros", "/mapa", "/participantes"):
            self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}{rota}", bia)[0], 404, rota)

        status, erro = self.requisitar("POST", f"/api/viagens/{vid}/participantes", ana,
                                       json={"email": "ninguem@email.com"})
        self.assertEqual(status, 404)
        status, dados = self.requisitar("POST", f"/api/viagens/{vid}/participantes", ana,
                                        json={"email": "bia@email.com", "papel": "viajante"})
        self.assertEqual(status, 201, dados)
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/participantes", ana,
                                         json={"email": "bia@email.com"})[0], 409)
        # Só o organizador convida
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/participantes", caio,
                                         json={"email": "caio@email.com"})[0], 404)

        # Convite pendente ainda não dá acesso
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}", bia)[0], 404)
        _, convites = self.requisitar("GET", "/api/convites", bia)
        self.assertEqual(convites["total"], 1)
        convite_id = convites["convites"][0]["id"]
        self.assertNotIn("observacoes", convites["convites"][0]["viagem"])
        self.assertEqual(self.requisitar("POST", f"/api/convites/{convite_id}/aceitar", caio)[0], 404)
        self.assertEqual(self.requisitar("POST", f"/api/convites/{convite_id}/aceitar", bia)[0], 200)

        # Viajante: lê, mas não edita
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}", bia)[0], 200)
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/despesas", bia,
                                         json={"descricao": "Hotel", "valor": 100})[0], 403)
        self.assertEqual(self.requisitar("PUT", f"/api/viagens/{vid}", bia, json={"viajantes": 9})[0], 403)
        self.assertEqual(self.requisitar("DELETE", f"/api/viagens/{vid}", bia)[0], 403)
        _, lista_bia = self.requisitar("GET", "/api/viagens", bia)
        self.assertEqual(lista_bia["viagens"][0]["meu_papel"], "viajante")
        _, participantes_bia = self.requisitar("GET", f"/api/viagens/{vid}/participantes", bia)
        self.assertNotIn("email", participantes_bia["participantes"][0]["usuario"])  # privacidade

        # Promovida a editora: passa a editar
        _, participantes = self.requisitar("GET", f"/api/viagens/{vid}/participantes", ana)
        pid = participantes["participantes"][0]["id"]
        self.assertEqual(self.requisitar("PATCH", f"/api/viagens/{vid}/participantes/{pid}", ana,
                                         json={"papel": "editor"})[0], 200)
        status, desp = self.requisitar("POST", f"/api/viagens/{vid}/despesas", bia,
                                       json={"descricao": "Hotel", "valor": 100, "categoria": "hospedagem",
                                             "pago_por_id": bia_id})
        self.assertEqual(status, 201, desp)
        self.assertEqual(self.requisitar("DELETE", f"/api/viagens/{vid}", bia)[0], 403)  # excluir: só dono

        # Sugestões e decisão do grupo
        museu = self.lugar_por_nome("Pelourinho")
        status, sug = self.requisitar("POST", f"/api/viagens/{vid}/sugestoes", bia,
                                      json={"lugar_id": museu, "descricao": "Ver os ensaios"})
        self.assertEqual(status, 201)
        sid = sug["sugestoes"][0]["id"]
        self.assertEqual(sug["sugestoes"][0]["votos_favor"], 1)
        _, votado = self.requisitar("POST", f"/api/sugestoes/{sid}/voto", ana, json={"valor": 1})
        self.assertEqual(votado["sugestoes"][0]["saldo"], 2)
        self.assertEqual(self.requisitar("POST", f"/api/sugestoes/{sid}/voto", ana, json={"valor": 5})[0], 422)
        _, decidido = self.requisitar("POST", f"/api/sugestoes/{sid}/decisao", ana,
                                      json={"decisao": "aprovada", "dia": 2})
        self.assertEqual(decidido["sugestoes"][0]["status"], "aprovada")
        _, roteiros = self.requisitar("GET", f"/api/viagens/{vid}/roteiros", ana)
        atividade = roteiros["ativo"]["atividades"][0]
        self.assertEqual((atividade["titulo"], atividade["dia"], atividade["lugar_id"]), ("Pelourinho", 2, museu))
        self.assertEqual(self.requisitar("POST", f"/api/sugestoes/{sid}/voto", bia, json={"valor": -1})[0], 400)

        # Remover participante corta o acesso; participante pode sair sozinho
        self.assertEqual(self.requisitar("DELETE", f"/api/viagens/{vid}/participantes/{pid}", ana)[0], 200)
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}", bia)[0], 404)
        self.requisitar("POST", f"/api/viagens/{vid}/participantes", ana, json={"email": "caio@email.com"})
        _, conv = self.requisitar("GET", "/api/convites", caio)
        self.requisitar("POST", f"/api/convites/{conv['convites'][0]['id']}/aceitar", caio)
        _, parts = self.requisitar("GET", f"/api/viagens/{vid}/participantes", caio)
        caio_pid = parts["participantes"][0]["id"]
        status, saiu = self.requisitar("DELETE", f"/api/viagens/{vid}/participantes/{caio_pid}", caio)
        self.assertTrue(saiu["saiu"])
        # Recusar convite
        self.requisitar("POST", f"/api/viagens/{vid}/participantes", ana, json={"email": "bia@email.com"})
        _, conv = self.requisitar("GET", "/api/convites", bia)
        self.assertEqual(self.requisitar("POST", f"/api/convites/{conv['convites'][0]['id']}/recusar", bia)[0], 200)
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}", bia)[0], 404)


class TestRoteiros(CasoComApp):
    def _viagem(self, token, dias=3):
        rio = self.lugar_por_nome("Museu do Amanhã")
        _, dados = self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Rio de Janeiro, RJ", "lugar_id": rio, "data_ida": d(5), "data_volta": d(5 + dias - 1)})
        return dados["viagem"]["id"]

    def test_gerar_versionar_e_editar(self):
        token, _ = self.criar_usuario(interesses=("museus", "aventura", "gastronomia"))
        vid = self._viagem(token)
        status, gerado = self.requisitar("POST", f"/api/viagens/{vid}/roteiros/gerar", token,
                                         json={"ritmo": "moderado"})
        self.assertEqual(status, 201, gerado)
        roteiro = gerado["roteiro"]
        self.assertEqual((roteiro["versao"], roteiro["ativo"], roteiro["origem"]), (1, True, "local"))
        with self.app.app_context():
            from backend.models.lugar import Lugar

            nomes_catalogo = {l.nome for l in Lugar.query.all()}
        for atividade in roteiro["atividades"]:
            self.assertTrue(1 <= atividade["dia"] <= 3)
            if atividade["fonte"] == "catalogo":  # nada inventado: tudo vem do catálogo
                self.assertIn(atividade["titulo"].split(": ")[-1], nomes_catalogo)
            else:
                self.assertIn(atividade["fonte"], ("sugestao", "openstreetmap"))
            if atividade["horario"]:
                self.assertTrue(atividade["horario_sugerido"])
        titulos = [a["titulo"] for a in roteiro["atividades"]]
        self.assertIn("Museu do Amanhã", titulos)  # o destino escolhido entra
        self.assertIn("Retorno", titulos)

        _, v2 = self.requisitar("POST", f"/api/viagens/{vid}/roteiros/gerar", token, json={"ritmo": "leve"})
        self.assertEqual(v2["roteiro"]["versao"], 2)
        _, lista = self.requisitar("GET", f"/api/viagens/{vid}/roteiros", token)
        self.assertEqual([v["ativo"] for v in lista["versoes"]], [True, False])
        self.assertEqual(self.requisitar("POST", f"/api/roteiros/{roteiro['id']}/ativar", token)[0], 200)
        _, lista = self.requisitar("GET", f"/api/viagens/{vid}/roteiros", token)
        self.assertEqual(lista["ativo"]["versao"], 1)

        status, copia = self.requisitar("POST", f"/api/roteiros/{roteiro['id']}/duplicar", token)
        self.assertEqual(len(copia["roteiro"]["atividades"]), len(roteiro["atividades"]))
        rid = copia["roteiro"]["id"]
        status, nova = self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token, json={
            "titulo": "Passeio de barco", "dia": 2, "horario": "15:00", "duracao_min": 90,
            "latitude": -22.9, "longitude": -43.17, "categoria": "experiencia"})
        self.assertEqual(status, 201, nova)
        self.assertFalse(nova["atividade"]["horario_sugerido"])
        aid = nova["atividade"]["id"]
        self.assertEqual(self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token,
                                         json={"titulo": "X", "dia": 99})[0], 422)
        self.assertEqual(self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token,
                                         json={"titulo": "Teste", "horario": "25:00"})[0], 422)
        _, editada = self.requisitar("PATCH", f"/api/atividades/{aid}", token, json={"dia": 3, "titulo": "Barco"})
        self.assertEqual((editada["atividade"]["dia"], editada["atividade"]["titulo"]), (3, "Barco"))
        _, atual = self.requisitar("GET", f"/api/roteiros/{rid}", token)
        itens = [{"id": a["id"], "dia": 1, "ordem": i} for i, a in enumerate(reversed(atual["atividades"]))]
        status, reorg = self.requisitar("PUT", f"/api/roteiros/{rid}/ordem", token, json={"itens": itens})
        self.assertEqual(status, 200, reorg)
        self.assertTrue(all(a["dia"] == 1 for a in reorg["roteiro"]["atividades"]))
        self.assertEqual(reorg["roteiro"]["atividades"][0]["id"], itens[0]["id"])
        self.assertEqual(self.requisitar("PUT", f"/api/roteiros/{rid}/ordem", token,
                                         json={"itens": [{"id": 999999, "dia": 1, "ordem": 0}]})[0], 422)
        self.assertEqual(self.requisitar("DELETE", f"/api/atividades/{aid}", token)[0], 200)
        self.assertEqual(self.requisitar("DELETE", f"/api/roteiros/{rid}", token)[0], 200)
        _, lista = self.requisitar("GET", f"/api/viagens/{vid}/roteiros", token)
        self.assertEqual(len(lista["versoes"]), 2)
        self.assertEqual(sum(v["ativo"] for v in lista["versoes"]), 1)

        # Outro usuário não acessa roteiro nem atividade
        intruso, _ = self.criar_usuario(nome="Intruso Silva", email="x@email.com")
        self.assertEqual(self.requisitar("GET", f"/api/roteiros/{roteiro['id']}", intruso)[0], 404)
        self.assertEqual(self.requisitar("DELETE", f"/api/atividades/{roteiro['atividades'][0]['id']}", intruso)[0], 404)

    def test_pontos_reais_do_openstreetmap_e_funcionamento(self):
        """Pontos OSM já em cache entram no roteiro; horário de funcionamento é respeitado."""
        token, _ = self.criar_usuario(email="osm@email.com", interesses=("museus",))
        vid = self._viagem(token, dias=1)
        with self.app.app_context():
            from backend.extensions import db
            from backend.models.ponto_interesse import PontoInteresse
            from backend.models.viagem import Viagem

            viagem = db.session.get(Viagem, vid)
            dia_semana = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"][viagem.data_ida.weekday()]
            db.session.add(PontoInteresse(osm_tipo="node", osm_id=1, nome="Museu Teste OSM", tipo="museu",
                                          latitude=viagem.latitude + 0.002, longitude=viagem.longitude,
                                          funcionamento=f"{dia_semana} 13:00-18:00"))
            db.session.commit()
        _, gerado = self.requisitar("POST", f"/api/viagens/{vid}/roteiros/gerar", token,
                                    json={"ritmo": "intenso", "incluir_refeicoes": False})
        osm = [a for a in gerado["roteiro"]["atividades"] if a["fonte"] == "openstreetmap"]
        self.assertEqual(len(osm), 1, gerado["roteiro"]["atividades"])
        self.assertGreaterEqual(osm[0]["horario"], "13:00")
        self.assertEqual(osm[0]["funcionamento"], f"{dia_semana} 13:00-18:00")

    def test_ia_nao_pode_inventar_lugares(self):
        """Gemini simulado: itens fora da lista de candidatos são descartados."""
        from backend.services.roteiro_inteligente_service import RoteiroInteligenteService

        class IAFalsa:
            configurado = True

            def gerar_json(self, prompt):
                chave = prompt.split('"chave": "')[1].split('"')[0]
                return {"observacoes": "ok", "dias": [{"dia": 1, "atividades": [
                    {"chave": "l:99999", "horario": "09:00"},
                    {"chave": chave, "horario": "10:00", "duracao_min": 60, "dica": "Chegue cedo"}]}]}

        token, _ = self.criar_usuario(email="ia@email.com")
        vid = self._viagem(token, dias=1)
        with self.app.app_context():
            from backend.extensions import db
            from backend.models.viagem import Viagem

            viagem = db.session.get(Viagem, vid)
            resultado = RoteiroInteligenteService(servico_ia=IAFalsa()).executar(
                viagem, {"interesses": ["museus"], "buscar_externo": False})
        self.assertEqual(resultado["origem"], "gemini")
        self.assertEqual(len(resultado["atividades"]), 1)
        self.assertIn("Chegue cedo", resultado["atividades"][0]["descricao"])


class TestFinancas(CasoComApp):
    def test_orcamento_despesas_e_alertas(self):
        token, uid = self.criar_usuario()
        _, v = self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Bonito, MS", "data_ida": d(3), "data_volta": d(6), "viajantes": 2, "orcamento": 1000})
        vid = v["viagem"]["id"]
        _, r1 = self.requisitar("POST", f"/api/viagens/{vid}/despesas", token, json={
            "descricao": "Pousada", "valor": "500,00", "categoria": "hospedagem", "data": d(3), "pago_por_id": uid})
        self.assertEqual(r1["financas"]["saldo"], 500.0)
        self.assertEqual(r1["financas"]["alertas"], [])
        _, r2 = self.requisitar("POST", f"/api/viagens/{vid}/despesas", token, json={
            "descricao": "Flutuação", "valor": 350.5, "categoria": "passeios"})
        f = r2["financas"]
        self.assertEqual((f["gasto"], f["saldo"], f["percentual_usado"]), (850.5, 149.5, 85.0))
        self.assertEqual(f["gasto_por_pessoa"], 425.25)
        self.assertEqual(f["orcamento_por_pessoa"], 500.0)
        self.assertEqual(f["alertas"][0]["nivel"], "aviso")
        por_cat = {c["categoria"]: c["gasto"] for c in f["categorias"]}
        self.assertEqual((por_cat["hospedagem"], por_cat["passeios"]), (500.0, 350.5))
        did = r2["despesa"]["id"]
        _, r3 = self.requisitar("PUT", f"/api/despesas/{did}", token, json={"valor": 700})
        self.assertEqual(r3["financas"]["alertas"][0]["nivel"], "erro")  # ultrapassou
        _, r4 = self.requisitar("PUT", f"/api/viagens/{vid}/orcamento", token, json={
            "orcamento": 2000, "planejamento": {"hospedagem": 400, "alimentacao": 300}})
        self.assertTrue(any("Hospedagem" in a["texto"] for a in r4["financas"]["alertas"]))
        for corpo in ({"descricao": "X1", "valor": -5}, {"descricao": "Táxi", "valor": 0},
                      {"descricao": "Táxi", "valor": "abc"}, {"descricao": "Táxi", "valor": 10, "categoria": "zz"},
                      {"descricao": "Táxi", "valor": 10, "pago_por_id": 99999}):
            self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/despesas", token, json=corpo)[0], 422, corpo)
        _, r5 = self.requisitar("DELETE", f"/api/despesas/{did}", token)
        self.assertEqual(r5["financas"]["gasto"], 500.0)
        outro, _ = self.criar_usuario(nome="Outra Pessoa", email="o@email.com")
        self.assertEqual(self.requisitar("DELETE", f"/api/despesas/{r1['despesa']['id']}", outro)[0], 404)


class TestChecklist(CasoComApp):
    def test_sugestoes_progresso_e_reuso(self):
        token, _ = self.criar_usuario(interesses=("praia",))
        sancho = self.lugar_por_nome("Baía do Sancho")
        _, v = self.requisitar("POST", "/api/viagens", token, json={
            "lugar_id": sancho, "data_ida": d(3), "data_volta": d(8)})
        vid = v["viagem"]["id"]
        _, lista = self.requisitar("POST", f"/api/viagens/{vid}/checklist/sugestoes", token)
        textos = [i["texto"] for i in lista["itens"]]
        self.assertIn("Protetor solar", textos)
        self.assertIn("Roupas para 6 dias (inclua uma muda extra)", textos)
        self.assertEqual(len(textos), len(set(textos)))
        _, de_novo = self.requisitar("POST", f"/api/viagens/{vid}/checklist/sugestoes", token)
        self.assertEqual(de_novo["total"], lista["total"])  # não duplica
        status, novo = self.requisitar("POST", f"/api/viagens/{vid}/checklist", token,
                                       json={"texto": "Máscara de snorkel", "categoria": "outros"})
        self.assertEqual(status, 201)
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/checklist", token,
                                         json={"texto": "máscara de SNORKEL"})[0], 422)
        _, marcado = self.requisitar("PATCH", f"/api/checklist/{novo['item']['id']}", token, json={"concluido": True})
        self.assertEqual(marcado["concluidos"], 1)
        self.assertEqual(marcado["percentual"], round(100 / marcado["total"]))
        _, removido = self.requisitar("DELETE", f"/api/checklist/{lista['itens'][0]['id']}", token)
        self.assertEqual(removido["total"], marcado["total"] - 1)

        _, v2 = self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Florianópolis, SC", "data_ida": d(40), "data_volta": d(42)})
        _, importado = self.requisitar("POST", f"/api/viagens/{v2['viagem']['id']}/checklist/importar", token,
                                       json={"origem_viagem_id": vid})
        self.assertEqual(importado["total"], removido["total"])
        self.assertEqual(importado["concluidos"], 0)  # reaproveita a lista, não o progresso
        intruso, _ = self.criar_usuario(nome="Intruso Lima", email="i@email.com")
        self.assertEqual(self.requisitar("PATCH", f"/api/checklist/{novo['item']['id']}", intruso,
                                         json={"concluido": False})[0], 404)


class TestCalendario(CasoComApp):
    def test_agenda_integra_roteiro_e_detecta_conflitos(self):
        token, _ = self.criar_usuario()
        rio = self.lugar_por_nome("Museu do Amanhã")
        _, v = self.requisitar("POST", "/api/viagens", token, json={
            "lugar_id": rio, "data_ida": d(7), "data_volta": d(9)})
        vid = v["viagem"]["id"]
        _, r = self.requisitar("POST", f"/api/viagens/{vid}/roteiros", token, json={"titulo": "Meu"})
        self.requisitar("POST", f"/api/roteiros/{r['roteiro']['id']}/atividades", token, json={
            "titulo": "Museu", "dia": 1, "horario": "10:00", "duracao_min": 120})
        self.requisitar("POST", f"/api/roteiros/{r['roteiro']['id']}/atividades", token, json={
            "titulo": "Praia livre", "dia": 2})
        status, c = self.requisitar("POST", f"/api/viagens/{vid}/compromissos", token, json={
            "titulo": "Almoço reservado", "tipo": "refeicao", "inicio": f"{d(7)}T11:30", "duracao_min": 60})
        self.assertEqual(status, 201, c)
        self.requisitar("POST", f"/api/viagens/{vid}/compromissos", token, json={
            "titulo": "Voo", "tipo": "transporte", "inicio": f"{d(9)}T18:00", "duracao_min": 90})
        _, cal = self.requisitar("GET", f"/api/viagens/{vid}/calendario", token)
        self.assertEqual(len(cal["dias"]), 3)
        self.assertEqual([e["origem"] for e in cal["eventos"]], ["roteiro", "agenda", "agenda"])
        self.assertEqual(len(cal["conflitos"]), 1)
        self.assertTrue(cal["eventos"][0]["conflito"] and cal["eventos"][1]["conflito"])
        self.assertFalse(cal["eventos"][2]["conflito"])
        self.assertEqual(cal["sem_horario"][0]["titulo"], "Praia livre")
        cid = c["compromisso"]["id"]
        self.requisitar("PUT", f"/api/compromissos/{cid}", token, json={"inicio": f"{d(7)}T13:00"})
        _, cal = self.requisitar("GET", f"/api/viagens/{vid}/calendario", token)
        self.assertEqual(cal["conflitos"], [])
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/compromissos", token, json={
            "titulo": "Fora", "inicio": f"{d(30)}T10:00"})[0], 422)
        self.assertEqual(self.requisitar("POST", f"/api/viagens/{vid}/compromissos", token, json={
            "titulo": "Sem data"})[0], 422)
        self.assertEqual(self.requisitar("DELETE", f"/api/compromissos/{cid}", token)[0], 200)


class TestAvaliacoes(CasoComApp):
    def test_avaliar_com_fotos_sem_duplicar(self):
        from PIL import Image

        token, _ = self.criar_usuario()
        outro, _ = self.criar_usuario(nome="Outro Viajante", email="outro@email.com")
        lugar = self.lugar_por_nome("Cataratas do Iguaçu")
        resposta = self.cliente.post(
            f"/api/lugares/{lugar}/avaliacoes", headers={"Authorization": f"Bearer {token}"},
            data={"nota": "5", "titulo": "Impressionante", "comentario": "As passarelas são incríveis!",
                  "fotos": [(imagem_png(), "foto.png")]}, content_type="multipart/form-data")
        self.assertEqual(resposta.status_code, 201, resposta.get_json())
        avaliacao = resposta.get_json()["avaliacao"]
        self.assertFalse(avaliacao["experiencia_verificada"])
        url = avaliacao["fotos"][0]["url"]
        self.assertEqual(self.cliente.get(url).status_code, 200)
        self.assertEqual(self.cliente.get(url.replace("sig=", "sig=0")).status_code, 404)  # adulterada
        self.assertEqual(self.cliente.get(url.split("?")[0]).status_code, 404)  # sem assinatura

        status, _ = self.requisitar("POST", f"/api/lugares/{lugar}/avaliacoes", token,
                                    json={"nota": 1, "comentario": "Tentando duplicar a nota"})
        self.assertEqual(status, 409)  # sem avaliações duplicadas
        for corpo in ({"nota": 6, "comentario": "comentário válido aqui"}, {"nota": 3, "comentario": "curto"},
                      {"nota": "x", "comentario": "comentário válido aqui"},
                      {"nota": 4, "comentario": "comentário válido aqui", "data_visita": d(3)}):
            self.assertEqual(self.requisitar("POST", f"/api/lugares/{lugar}/avaliacoes", outro, json=corpo)[0], 422)
        falsa = self.cliente.post(f"/api/lugares/{lugar}/avaliacoes", headers={"Authorization": f"Bearer {outro}"},
                                  data={"nota": "4", "comentario": "Arquivo falso anexado",
                                        "fotos": [(io.BytesIO(b"<script>alert(1)</script>" * 4), "x.jpg")]},
                                  content_type="multipart/form-data")
        self.assertEqual(falsa.status_code, 422)
        self.requisitar("POST", f"/api/lugares/{lugar}/avaliacoes", outro, json={"nota": 3, "comentario": "Bom, mas lotado."})
        _, listagem = self.requisitar("GET", f"/api/lugares/{lugar}/avaliacoes", token)
        self.assertEqual(listagem["comunidade"]["total"], 2)
        self.assertEqual(listagem["comunidade"]["media"], 4.0)
        self.assertEqual(listagem["comunidade"]["distribuicao"]["5"], 1)
        self.assertEqual(listagem["minha"]["id"], avaliacao["id"])
        self.assertNotEqual(listagem["catalogo"]["nota"], None)  # nota do catálogo fica separada

        # Editar/excluir: só o autor
        self.assertEqual(self.requisitar("PUT", f"/api/avaliacoes/{avaliacao['id']}", outro,
                                         json={"nota": 1, "comentario": "sabotando a nota"})[0], 404)
        self.assertEqual(self.requisitar("DELETE", f"/api/avaliacoes/{avaliacao['id']}", outro)[0], 404)

        # Experiência verificada: viagem concluída com o lugar
        self.requisitar("POST", "/api/viagens", token, json={
            "lugar_id": lugar, "data_ida": d(-20), "data_volta": d(-17)})
        _, editada = self.requisitar("PUT", f"/api/avaliacoes/{avaliacao['id']}", token, json={"nota": 4})
        self.assertTrue(editada["avaliacao"]["experiencia_verificada"])
        self.assertEqual(editada["avaliacao"]["nota"], 4)

        # Privacidade: o arquivo salvo não tem metadados EXIF
        with self.app.app_context():
            from backend.models.avaliacao import FotoAvaliacao
            from backend.utils.arquivos import pasta

            arquivo = FotoAvaliacao.query.first().arquivo
            caminho = os.path.join(pasta("avaliacoes"), arquivo)
        self.assertFalse(Image.open(caminho).info.get("exif"))
        self.assertEqual(self.requisitar("DELETE", f"/api/avaliacoes/{avaliacao['id']}/fotos/"
                                                   f"{avaliacao['fotos'][0]['id']}", token)[0], 200)
        self.assertFalse(os.path.exists(caminho))
        self.assertEqual(self.requisitar("DELETE", f"/api/avaliacoes/{avaliacao['id']}", token)[0], 200)
        _, comunidade = self.requisitar("GET", "/api/comunidade")
        self.assertEqual(len(comunidade["itens"]), 1)

    def test_exif_gps_removido(self):
        from PIL import Image

        token, _ = self.criar_usuario(email="gps@email.com")
        imagem = Image.new("RGB", (60, 40), (10, 120, 200))
        exif = Image.Exif()
        exif[0x8825] = {2: (23.0, 33.0, 0.0)}  # bloco GPS
        exif[0x010F] = "CameraTeste"
        saida = io.BytesIO()
        imagem.save(saida, "JPEG", exif=exif.tobytes())
        self.assertTrue(Image.open(io.BytesIO(saida.getvalue())).info.get("exif"))
        saida.seek(0)
        resposta = self.cliente.post("/api/diario", headers={"Authorization": f"Bearer {token}"},
                                     data={"titulo": "Pôr do sol", "data": d(-1), "fotos": [(saida, "gps.jpg")]},
                                     content_type="multipart/form-data")
        self.assertEqual(resposta.status_code, 201, resposta.get_json())
        url = resposta.get_json()["registro"]["fotos"][0]["url"]
        baixada = self.cliente.get(url)
        self.assertFalse(Image.open(io.BytesIO(baixada.data)).info.get("exif"))


class TestDiario(CasoComApp):
    def test_registros_visibilidade_e_estatisticas(self):
        token, _ = self.criar_usuario()
        amigo, _ = self.criar_usuario(nome="Amigo Teste", email="amigo@email.com")
        ouro = self.lugar_por_nome("Centro Histórico de Ouro Preto")
        _, v = self.requisitar("POST", "/api/viagens", token, json={
            "lugar_id": ouro, "data_ida": d(-40), "data_volta": d(-36)})
        vid = v["viagem"]["id"]
        self.requisitar("POST", f"/api/viagens/{vid}/participantes", token, json={"email": "amigo@email.com"})
        _, conv = self.requisitar("GET", "/api/convites", amigo)
        self.requisitar("POST", f"/api/convites/{conv['convites'][0]['id']}/aceitar", amigo)

        self.assertEqual(self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Amanhã", "data": d(2)})[0], 422)
        self.assertEqual(self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Sem viagem", "data": d(-1), "visibilidade": "participantes"})[0], 422)
        status, privado = self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Igrejas barrocas", "relato": "Dia lindo.", "viagem_id": vid, "lugar_id": ouro,
            "nota_pessoal": 5, "data": d(-39)})
        self.assertEqual(status, 201, privado)
        self.assertEqual(privado["registro"]["visibilidade"], "privado")
        self.assertEqual(privado["registro"]["cidade"], "Ouro Preto")
        self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Jantar com o grupo", "viagem_id": vid, "data": d(-38), "visibilidade": "participantes"})
        self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Dica pública", "lugar_id": ouro, "data": d(-37), "visibilidade": "publico", "nota_pessoal": 4})
        self.requisitar("POST", "/api/diario", token, json={
            "titulo": "Viagem antiga", "data": "2019-05-10", "cidade": "Lisboa", "estado": "Portugal"})

        _, da_viagem = self.requisitar("GET", f"/api/viagens/{vid}/diario", amigo)
        self.assertEqual([r["titulo"] for r in da_viagem["registros"]], ["Jantar com o grupo"])
        intruso, _ = self.criar_usuario(nome="Intruso Costa", email="intr@email.com")
        self.assertEqual(self.requisitar("GET", f"/api/viagens/{vid}/diario", intruso)[0], 404)
        self.assertEqual(self.requisitar("PUT", f"/api/diario/{privado['registro']['id']}", amigo,
                                         json={"titulo": "Hackeado"})[0], 404)

        _, diario = self.requisitar("GET", "/api/diario", token)
        self.assertEqual(diario["total"], 4)
        self.assertEqual(diario["linha_do_tempo"][-1]["ano"], "2019")  # cronológico
        _, est = self.requisitar("GET", "/api/diario/estatisticas", token)
        self.assertEqual(est["viagens_concluidas"], 1)
        self.assertEqual(est["dias_viajados"], 5)
        self.assertIn("MG", est["estados_visitados"])
        self.assertEqual(est["registros"], 4)
        self.assertEqual(est["nota_media_pessoal"], 4.5)
        self.assertEqual(est["categoria_favorita"], "cultura")

        _, avaliacoes = self.requisitar("GET", f"/api/lugares/{ouro}/avaliacoes")
        self.assertEqual([e["titulo"] for e in avaliacoes["experiencias"]], ["Dica pública"])
        _, comunidade = self.requisitar("GET", "/api/comunidade")
        self.assertEqual([i["relato"]["titulo"] for i in comunidade["itens"]], ["Dica pública"])
        _, editado = self.requisitar("PUT", f"/api/diario/{privado['registro']['id']}", token,
                                     json={"visibilidade": "publico"})
        self.assertEqual(editado["registro"]["visibilidade"], "publico")
        self.assertEqual(self.requisitar("DELETE", f"/api/diario/{privado['registro']['id']}", token)[0], 200)


class ClienteFalso:
    """Simula as respostas da API da Wikimedia (sem rede)."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.chamadas = []

    def requisitar_json(self, url, params=None, **_):
        self.chamadas.append((url, params))
        if "wikipedia" in url:
            if params.get("titles") == "Cataratas do Iguaçu":
                return self.respostas["artigo"]
            return {"query": {"pages": []}}
        if params.get("list") == "geosearch":
            return self.respostas["geo"]
        return self.respostas["info"]


def _info(titulo, licenca="CC BY-SA 4.0", largura=4000, altura=2600):
    nome = titulo.replace("File:", "").replace(" ", "_")
    return {
        "title": titulo,
        "imageinfo": [{
            "url": f"https://upload.wikimedia.org/wikipedia/commons/a/ab/{nome}",
            "thumburl": f"https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/{nome}/1280px-{nome}",
            "descriptionurl": f"https://commons.wikimedia.org/wiki/{titulo}",
            "width": largura, "height": altura, "mime": "image/jpeg",
            "extmetadata": {"LicenseShortName": {"value": licenca}, "Artist": {"value": "<a href='x'>Fotógrafa</a>"},
                            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"}},
        }],
    }


class TestFotosReais(CasoComApp):
    def test_sincronizacao_wikimedia_simulada_e_curadoria(self):
        from backend.services.fotos_lugar_service import CurarFotoService, SincronizarFotosService
        from backend.services.integracoes.fotos_wikimedia_service import FotosWikimediaService

        lugar = self.lugar_por_nome("Cataratas do Iguaçu")
        status, sem_foto = self.requisitar("GET", f"/api/lugares/{lugar}/fotos")
        self.assertEqual(sem_foto["fotos"], [])
        self.assertIn("ilustração", sem_foto["ilustracao"]["aviso"])
        self.assertFalse(self.requisitar("GET", "/api/vitrine/fundo")[1]["disponivel"])

        respostas = {
            "artigo": {"query": {"pages": [{"title": "Cataratas do Iguaçu", "pageimage": "Iguacu_principal.jpg",
                                            "coordinates": [{"lat": -25.6953, "lon": -54.4367}]}]}},
            "geo": {"query": {"geosearch": [
                {"title": "File:Garganta do Diabo Iguazu.jpg"},
                {"title": "File:Hotel qualquer.jpg"},             # sem o nome do lugar: ignorada
                {"title": "File:Iguacu mapa.svg"},                # não é foto: ignorada
            ]}},
            "info": {"query": {"pages": [
                _info("File:Iguacu_principal.jpg"),
                _info("File:Garganta do Diabo Iguazu.jpg", licenca="CC BY 2.0"),
            ]}},
        }
        with self.app.app_context():
            from backend.extensions import db
            from backend.models.foto_lugar import FotoLugar
            from backend.models.lugar import Lugar

            wikimedia = FotosWikimediaService(cliente=ClienteFalso(respostas))
            relatorio = SincronizarFotosService(provedores={"wikimedia": wikimedia}).executar(lugar_ids=[lugar])
            self.assertEqual((relatorio["novas"], relatorio["verificadas"]), (2, 2), relatorio)
            # Licença não livre é recusada
            proibida = {"query": {"pages": [_info("File:Iguacu_principal.jpg", licenca="All rights reserved")]}}
            self.assertEqual(FotosWikimediaService(cliente=ClienteFalso({**respostas, "info": proibida}))
                             ._informacoes(["File:Iguacu_principal.jpg"]), [])
            # Candidata de busca por texto (Pexels) entra como NÃO verificada
            SincronizarFotosService.gravar(db.session.get(Lugar, lugar), [{
                "fonte": "pexels", "url": "https://images.pexels.com/photos/1/x.jpg", "autor": "Alguém",
                "verificada": False, "criterio": "busca por texto"}])
            candidata = FotoLugar.query.filter_by(fonte="pexels").first().id

        _, fotos = self.requisitar("GET", f"/api/lugares/{lugar}/fotos")
        self.assertEqual(len(fotos["fotos"]), 2)
        principal = fotos["fotos"][0]
        self.assertTrue(principal["principal"])
        self.assertEqual(principal["autor"], "Fotógrafa")  # HTML removido da atribuição
        self.assertIn("480px-", principal["miniatura"])
        self.assertIn("1920px-", principal["url"])
        self.assertNotIn("pexels", json.dumps(fotos))
        _, detalhe = self.requisitar("GET", f"/api/lugares/{lugar}")
        self.assertEqual(detalhe["foto"]["id"], principal["id"])
        self.assertEqual(detalhe["total_fotos"], 2)
        _, fundo = self.requisitar("GET", "/api/vitrine/fundo")
        self.assertTrue(fundo["disponivel"])
        self.assertEqual([f["largura"] for f in fundo["fontes"]], [960, 1600, 2400])
        self.assertIn("Fotógrafa", fundo["credito"]["autor"])

        with self.app.app_context():
            CurarFotoService().aprovar(candidata)
        _, fotos = self.requisitar("GET", f"/api/lugares/{lugar}/fotos")
        self.assertEqual(len(fotos["fotos"]), 3)

    def test_coordenadas_divergentes_nao_verificam(self):
        """Artigo homônimo longe do lugar real não é aceito."""
        from backend.services.integracoes.fotos_wikimedia_service import FotosWikimediaService

        respostas = {
            "artigo": {"query": {"pages": [{"title": "Cataratas do Iguaçu", "pageimage": "Outro.jpg",
                                            "coordinates": [{"lat": -3.0, "lon": -60.0}]}]}},
            "geo": {"query": {"geosearch": []}}, "info": {"query": {"pages": []}},
        }
        lugar_id = self.lugar_por_nome("Cataratas do Iguaçu")
        with self.app.app_context():
            from backend.extensions import db
            from backend.models.lugar import Lugar

            lugar = db.session.get(Lugar, lugar_id)
            candidatas = FotosWikimediaService(cliente=ClienteFalso(respostas)).executar(
                lugar, {"wikipedia": {"pt": "Cataratas do Iguaçu"}, "raio_km": 8})
        self.assertEqual(candidatas, [])

    def test_sem_rede_nao_quebra(self):
        from backend.services.fotos_lugar_service import SincronizarFotosService

        with self.app.app_context():
            relatorio = SincronizarFotosService().executar(lugar_ids=[1])
        self.assertTrue(relatorio["erros"])
        self.assertEqual(relatorio["novas"], 0)


class TestMapaEComparador(CasoComApp):
    def test_mapa_da_viagem(self):
        token, _ = self.criar_usuario()
        self.assertEqual(self.requisitar("GET", "/api/mapa/config")[1]["tile_url"],
                         "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
        _, lugares = self.requisitar("GET", "/api/mapa/lugares")
        self.assertEqual(len(lugares["lugares"]), 20)
        rio = self.lugar_por_nome("Museu do Amanhã")
        _, v = self.requisitar("POST", "/api/viagens", token, json={"lugar_id": rio, "data_ida": d(4), "data_volta": d(5)})
        vid = v["viagem"]["id"]
        _, r = self.requisitar("POST", f"/api/viagens/{vid}/roteiros", token, json={})
        rid = r["roteiro"]["id"]
        self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token, json={
            "titulo": "Museu", "dia": 1, "horario": "09:00", "lugar_id": rio})
        self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token, json={
            "titulo": "Pedra Bonita", "dia": 1, "horario": "14:00", "lugar_id": self.lugar_por_nome("Trilha da Pedra Bonita")})
        self.requisitar("POST", f"/api/roteiros/{rid}/atividades", token, json={"titulo": "Sem local", "dia": 2})
        _, mapa = self.requisitar("GET", f"/api/viagens/{vid}/mapa", token)
        self.assertEqual(len(mapa["pontos"]), 3)  # destino + 2 atividades com coordenadas
        trecho = mapa["trajetos"][0]["trechos"][0]
        self.assertTrue(10 < trecho["distancia_km"] < 25, trecho)  # Haversine real, em linha reta
        _, prox = self.requisitar("GET", f"/api/lugares/{rio}/proximidades")
        self.assertTrue(prox["aviso"])  # integrações desligadas: avisa em vez de inventar
        self.assertEqual(prox["pontos"], [])
        self.assertIn("Oteque", [c["nome"] for c in prox["catalogo"]])

    def test_comparador(self):
        token, _ = self.criar_usuario(interesses=("praia",))
        ids = [self.lugar_por_nome(n) for n in ("Baía do Sancho", "Praia do Rosa", "MASP")]
        status, comp = self.requisitar("GET", f"/api/comparador?ids={','.join(map(str, ids))}", token)
        self.assertEqual(status, 200, comp)
        self.assertEqual(len(comp["itens"]), 3)
        self.assertTrue(comp["personalizado"])
        self.assertEqual(comp["destaques"]["melhor_nota"], [ids[0]])
        self.assertEqual(comp["destaques"]["menor_preco"], [ids[2]])
        self.assertEqual(comp["destaques"]["mais_perto"], [ids[2]])  # MASP fica em São Paulo
        self.assertIsNone(comp["itens"][0]["clima"])  # sem rede: não inventa clima
        self.assertEqual(comp["itens"][0]["compatibilidade"]["combina_com"], ["Praia"])
        self.assertEqual(self.requisitar("GET", f"/api/comparador?ids={ids[0]}")[0], 422)
        self.assertEqual(self.requisitar("GET", "/api/comparador?ids=1,2,3,4")[0], 422)
        self.assertEqual(self.requisitar("GET", "/api/comparador?ids=1,abc")[0], 422)
        self.assertEqual(self.requisitar("GET", f"/api/comparador?ids={ids[0]},{ids[1]}")[0], 200)  # sem login


class TestVai(CasoComApp):
    def test_permissoes_contexto_e_acoes(self):
        token, _ = self.criar_usuario()
        outro, _ = self.criar_usuario(nome="Outra Conta", email="outra@email.com")
        _, perm = self.requisitar("GET", "/api/chat/permissoes", token)
        self.assertFalse(any(e["ativo"] for e in perm["escopos"]))  # tudo começa desligado
        _, v = self.requisitar("POST", "/api/viagens", token, json={
            "destino": "Bonito, MS", "data_ida": d(10), "data_volta": d(12), "orcamento": 2000})
        vid = v["viagem"]["id"]
        self.requisitar("POST", f"/api/viagens/{vid}/despesas", token, json={"descricao": "Pousada", "valor": 800})

        _, resposta = self.requisitar("POST", "/api/chat", token, json={"texto": "como estão os gastos da minha viagem?"})
        self.assertIn("autorização", resposta["resposta"]["texto"])
        self.assertNotIn("800", resposta["resposta"]["texto"])

        self.requisitar("PUT", "/api/chat/permissoes", token, json={"usar_viagens": True})
        _, resposta = self.requisitar("POST", "/api/chat", token, json={"texto": "como estão os gastos da minha viagem?"})
        self.assertIn("Orçamentos e gastos", resposta["resposta"]["texto"])  # finanças pedem permissão própria
        self.requisitar("PUT", "/api/chat/permissoes", token, json={"usar_financas": True})
        _, resposta = self.requisitar("POST", "/api/chat", token, json={"texto": "como estão os gastos da minha viagem?"})
        self.assertIn("R$ 800,00", resposta["resposta"]["texto"])
        self.assertEqual(resposta["acoes"][0]["tipo"], "abrir_viagem")

        _, resposta = self.requisitar("POST", "/api/chat", token, json={"texto": "quero ir para Bonito, pode planejar?"})
        self.assertEqual(resposta["acoes"][0]["tipo"], "criar_viagem")
        self.assertEqual(resposta["acoes"][0]["lugar_id"], self.lugar_por_nome("Flutuação no Rio da Prata"))
        # Não é possível usar a viagem de outra pessoa como contexto
        self.assertEqual(self.requisitar("POST", "/api/chat", outro, json={"texto": "minha viagem", "viagem_id": vid})[0], 404)
        _, foco = self.requisitar("POST", "/api/chat", token, json={"texto": "e a agenda?", "viagem_id": vid})
        self.assertIn("agenda", foco["resposta"]["texto"].lower())


class TestSeguranca(CasoComApp):
    def test_limite_de_requisicoes(self):
        from backend.utils.limite_requisicoes import limpar_limites

        self.app.config["LIMITE_REQUISICOES_ATIVO"] = True
        limpar_limites()
        try:
            codigos = [self.requisitar("POST", "/api/auth/login", json={"email": "a@b.com", "senha": "x"})[0]
                       for _ in range(11)]
        finally:
            self.app.config["LIMITE_REQUISICOES_ATIVO"] = False
        self.assertEqual(codigos[:10], [401] * 10)
        self.assertEqual(codigos[10], 429)

    def test_envio_grande_demais(self):
        token, _ = self.criar_usuario()
        grande = io.BytesIO(b"\xff\xd8\xff" + b"0" * (self.app.config["MAX_CONTENT_LENGTH"] + 10))
        resposta = self.cliente.post("/api/diario", headers={"Authorization": f"Bearer {token}"},
                                     data={"titulo": "x", "fotos": [(grande, "g.jpg")]},
                                     content_type="multipart/form-data")
        self.assertEqual(resposta.status_code, 413)


class TestMigracaoBancoExistente(unittest.TestCase):
    def test_banco_antigo_e_preservado(self):
        """Um banco criado pela versão anterior ganha as tabelas novas sem perder dados."""
        import tempfile

        from sqlalchemy import create_engine, inspect, text

        from backend.app import create_app
        from backend.extensions import db
        from backend.tests.apoio import criar_config

        pasta = tempfile.mkdtemp()
        caminho = os.path.join(pasta, "antigo.db")
        motor = create_engine(f"sqlite:///{caminho}")
        with motor.begin() as conexao:  # esquema mínimo da versão anterior
            conexao.execute(text("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome VARCHAR(120) NOT NULL, "
                                 "email VARCHAR(120) UNIQUE NOT NULL, senha_hash VARCHAR(255) NOT NULL, "
                                 "verificado BOOLEAN NOT NULL, token VARCHAR(64), criado_em DATETIME NOT NULL)"))
            conexao.execute(text("INSERT INTO usuarios VALUES (1, 'Pessoa Antiga', 'antiga@email.com', 'h', 1, NULL, "
                                 "'2025-01-01 00:00:00')"))
        motor.dispose()
        app = create_app(criar_config(caminho))
        with app.app_context():
            tabelas = set(inspect(db.engine).get_table_names())
            self.assertTrue({"viagens", "fotos_lugar", "avaliacoes", "migracoes_aplicadas"} <= tabelas)
            self.assertEqual(db.session.execute(text("SELECT nome FROM usuarios WHERE id=1")).scalar(), "Pessoa Antiga")
            db.session.remove()
            db.engine.dispose()
        app2 = create_app(criar_config(caminho))  # segunda subida: migração não roda de novo
        with app2.app_context():
            self.assertEqual(db.session.execute(text("SELECT COUNT(*) FROM migracoes_aplicadas")).scalar(), 1)
            db.session.remove()
            db.engine.dispose()


if __name__ == "__main__":
    unittest.main(verbosity=2)
