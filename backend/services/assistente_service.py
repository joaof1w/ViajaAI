"""Casos de uso da expansão do Vai (assistente existente) — sem criar um segundo assistente.

    ObterPermissoesAssistenteService · SalvarPermissoesAssistenteService
    MontarContextoAssistenteService (dados que o Vai pode usar, conforme consentimento)
    SugerirAcoesAssistenteService (atalhos: criar viagem, gerar roteiro, abrir agenda...)
"""
import re
import unicodedata

from backend.models.diario import RegistroDiario
from backend.models.lugar import Lugar
from backend.models.permissao_assistente import ESCOPOS_ASSISTENTE, PermissaoAssistente
from backend.repositories.favorito_repository import FavoritoRepository
from backend.repositories.viagem_repository import ViagemRepository
from backend.services.autorizacao_viagem_service import AutorizacaoViagemService
from backend.services.calendario_service import ObterCalendarioService
from backend.services.financas_service import ResumoFinanceiroService
from backend.utils.datas import hoje
from backend.utils.validadores import validar_booleano


def _normalizar(texto):
    texto = unicodedata.normalize("NFD", (texto or "").lower())
    return re.sub(r"[̀-ͯ]", "", texto)


class ObterPermissoesAssistenteService:
    def executar(self, usuario):
        return PermissaoAssistente.do_usuario(usuario.id).to_dict()


class SalvarPermissoesAssistenteService:
    def executar(self, usuario, dados):
        permissao = PermissaoAssistente.do_usuario(usuario.id)
        for chave in ESCOPOS_ASSISTENTE:
            if chave in dados:
                setattr(permissao, chave, validar_booleano(dados[chave]))
        permissao.salvar()
        return {"mensagem": "Permissões do Vai atualizadas.", **permissao.to_dict()}


class MontarContextoAssistenteService:
    def __init__(self, repositorio=None, autorizacao=None):
        self.repositorio = repositorio or ViagemRepository()
        self.autorizacao = autorizacao or AutorizacaoViagemService()

    def executar(self, usuario, viagem_id=None):
        permissao = PermissaoAssistente.do_usuario(usuario.id)
        contexto = {"permissoes": {k: bool(getattr(permissao, k)) for k in ESCOPOS_ASSISTENTE}}

        if permissao.usar_favoritos:
            contexto["favoritos"] = [
                {"nome": f.lugar.nome, "local": f"{f.lugar.cidade}, {f.lugar.estado}", "categoria": f.lugar.categoria}
                for f in FavoritoRepository().listar_com_lugar(usuario.id)[:10] if f.lugar
            ]

        viagens = []
        if permissao.usar_viagens:
            viagens = [v for v in self.repositorio.listar_do_usuario(usuario.id) if v.status != "concluida"]
            viagens.sort(key=lambda v: v.data_ida)
            viagens = viagens[:3]
        # Selecionar uma viagem no chat é um consentimento explícito para usar os dados dela.
        foco = None
        if viagem_id:
            foco = self.autorizacao.executar(viagem_id, usuario, "leitura")
            viagens = [foco] + [v for v in viagens if v.id != foco.id]

        contexto["viagens"] = [self._resumo_viagem(v, usuario, permissao.usar_financas or v is foco, v is foco)
                               for v in viagens]
        contexto["viagem_foco_id"] = foco.id if foco else None

        if permissao.usar_diario:
            registros = (RegistroDiario.query.filter_by(usuario_id=usuario.id)
                         .order_by(RegistroDiario.data.desc()).limit(5).all())
            contexto["diario"] = [
                {"titulo": r.titulo, "local": r.local or r.cidade, "data": r.data.isoformat(), "nota": r.nota_pessoal}
                for r in registros
            ]
        return contexto

    @staticmethod
    def _resumo_viagem(viagem, usuario, incluir_financas, foco):
        dados = {
            "id": viagem.id, "titulo": viagem.titulo, "destino": viagem.destino, "status": viagem.status,
            "data_ida": viagem.data_ida.isoformat(), "data_volta": viagem.data_volta.isoformat(),
            "duracao_dias": viagem.duracao_dias, "viajantes": viagem.viajantes, "foco": foco,
            "dias_para_partir": (viagem.data_ida - hoje()).days,
        }
        roteiro = viagem.roteiro_ativo
        if roteiro:
            dados["roteiro"] = [
                {"dia": a.dia, "titulo": a.titulo, "horario": a.horario} for a in roteiro.atividades[:24]
            ]
        agenda = ObterCalendarioService().executar(viagem.id, usuario)
        dados["agenda"] = [
            {"titulo": e["titulo"], "inicio": e["inicio"], "origem": e["origem"], "conflito": e["conflito"]}
            for e in agenda["eventos"][:15]
        ]
        dados["conflitos"] = len(agenda["conflitos"])
        if incluir_financas:
            financas = ResumoFinanceiroService.montar(viagem, usuario)
            dados["financas"] = {k: financas[k] for k in ("orcamento", "gasto", "saldo", "percentual_usado",
                                                          "gasto_por_pessoa")}
            dados["financas"]["por_categoria"] = {c["rotulo"]: c["gasto"] for c in financas["categorias"] if c["gasto"]}
            dados["financas"]["alertas"] = [a["texto"] for a in financas["alertas"]]
        if viagem.itens_checklist:
            feitos = sum(1 for i in viagem.itens_checklist if i.concluido)
            dados["checklist"] = {"total": len(viagem.itens_checklist), "concluidos": feitos,
                                  "pendentes": [i.texto for i in viagem.itens_checklist if not i.concluido][:8]}
        return dados


class SugerirAcoesAssistenteService:
    """Detecta intenções simples na pergunta e devolve atalhos para as telas certas."""

    def executar(self, pergunta, contexto):
        texto = _normalizar(pergunta)
        acoes = []
        foco = next((v for v in contexto.get("viagens", []) if v.get("foco")), None)
        quer_planejar = any(p in texto for p in ("criar viagem", "planejar", "quero ir", "organizar uma viagem",
                                                 "nova viagem", "montar viagem"))
        if quer_planejar:
            for lugar in Lugar.listar_todos():
                nomes = {_normalizar(lugar.nome), _normalizar(lugar.cidade)}
                if any(len(n) > 3 and n in texto for n in nomes):
                    acoes.append({"tipo": "criar_viagem", "rotulo": f"Planejar viagem para {lugar.nome}",
                                  "lugar_id": lugar.id})
                    break
            else:
                acoes.append({"tipo": "criar_viagem", "rotulo": "Criar uma nova viagem"})
        alvo = foco or (contexto.get("viagens") or [None])[0]
        if alvo:
            if any(p in texto for p in ("roteiro", "itinerario", "programacao")):
                acoes.append({"tipo": "gerar_roteiro", "rotulo": f"Gerar roteiro de {alvo['titulo']}", "viagem_id": alvo["id"]})
            if any(p in texto for p in ("gasto", "orcamento", "dinheiro", "custo")):
                acoes.append({"tipo": "abrir_viagem", "aba": "gastos", "rotulo": "Abrir gastos da viagem", "viagem_id": alvo["id"]})
            if any(p in texto for p in ("agenda", "calendario", "compromisso", "horario")):
                acoes.append({"tipo": "abrir_viagem", "aba": "agenda", "rotulo": "Abrir agenda da viagem", "viagem_id": alvo["id"]})
            if any(p in texto for p in ("mala", "checklist", "levar", "bagagem")):
                acoes.append({"tipo": "abrir_viagem", "aba": "checklist", "rotulo": "Abrir checklist", "viagem_id": alvo["id"]})
        if any(p in texto for p in ("comparar", "qual e melhor", "qual o melhor")):
            acoes.append({"tipo": "comparar", "rotulo": "Comparar destinos"})
        return acoes[:3]
