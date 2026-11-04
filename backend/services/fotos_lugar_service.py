"""Casos de uso das Fotografias Reais dos lugares (features 11 e 12).

    ListarFotosLugarService · SincronizarFotosService · CurarFotoService
    ObterFundoInicialService · sincronizar_em_segundo_plano()

As chaves de API (Pexels/Unsplash) ficam só no backend; o navegador recebe apenas
URLs públicas das imagens e os dados de atribuição.
"""
import json
import os
import threading

from backend.config import BASE_DIR, Config
from backend.extensions import db
from backend.models.foto_lugar import FotoLugar
from backend.models.lugar import Lugar
from backend.seeds import LUGARES_FUNDO_INICIAL, REFERENCIAS_FOTOS
from backend.services.integracoes.fotos_pexels_service import FotosPexelsService
from backend.services.integracoes.fotos_unsplash_service import FotosUnsplashService
from backend.services.integracoes.fotos_wikimedia_service import FotosWikimediaService, miniatura
from backend.utils.erros import IntegracaoIndisponivel, NaoEncontrado

PASTA_FUNDO = os.path.join(BASE_DIR, "frontend", "assets", "fundo")
CAMPOS_FOTO = ("fonte", "id_externo", "url", "url_media", "url_miniatura", "largura", "altura", "titulo", "autor",
               "autor_url", "licenca", "licenca_url", "pagina_origem", "verificada")


class ListarFotosLugarService:
    def executar(self, lugar_id):
        lugar = Lugar.buscar_por_id(lugar_id)
        if lugar is None:
            raise NaoEncontrado("Lugar não encontrado.")
        fotos = lugar.fotos_verificadas
        return {
            "lugar_id": lugar.id,
            "fotos": [f.to_dict() for f in fotos],
            "ilustracao": None if fotos else {
                "imagem": lugar.imagem,
                "aviso": "Ainda não há fotografia verificada deste lugar. Exibindo uma ilustração.",
            },
        }


class SincronizarFotosService:
    """Busca candidatas nas fontes e grava em FotoLugar (sem duplicar URLs)."""

    def __init__(self, provedores=None):
        self.provedores = provedores or {
            "wikimedia": FotosWikimediaService(),
            "pexels": FotosPexelsService(),
            "unsplash": FotosUnsplashService(),
        }

    def executar(self, lugar_ids=None, fontes=("wikimedia",), somente_sem_fotos=True, limite_por_lugar=5):
        consulta = db.session.query(Lugar)
        if lugar_ids:
            consulta = consulta.filter(Lugar.id.in_(lugar_ids))
        relatorio = {"lugares": 0, "novas": 0, "verificadas": 0, "erros": []}
        for lugar in consulta.order_by(Lugar.id).all():
            if somente_sem_fotos and lugar.fotos_verificadas:
                continue
            relatorio["lugares"] += 1
            referencia = REFERENCIAS_FOTOS.get(lugar.nome, {})
            for fonte in fontes:
                provedor = self.provedores.get(fonte)
                if provedor is None:
                    continue
                try:
                    candidatas = provedor.executar(lugar, referencia, limite=limite_por_lugar)
                except IntegracaoIndisponivel as erro:
                    relatorio["erros"].append(f"{lugar.nome} ({fonte}): {erro.mensagem}")
                    continue
                novas, verificadas = self.gravar(lugar, candidatas)
                relatorio["novas"] += novas
                relatorio["verificadas"] += verificadas
        return relatorio

    @staticmethod
    def gravar(lugar, candidatas):
        existentes = {f.url for f in lugar.fotos}
        novas = verificadas = 0
        ordem = max((f.ordem for f in lugar.fotos), default=0)
        tem_principal = any(f.principal and f.verificada for f in lugar.fotos)
        for candidata in candidatas:
            if candidata["url"] in existentes:
                continue
            ordem += 1
            foto = FotoLugar(lugar_id=lugar.id, ordem=ordem, criterio_verificacao=candidata.get("criterio"),
                             **{c: candidata.get(c) for c in CAMPOS_FOTO})
            foto.verificada = bool(candidata.get("verificada"))
            if foto.verificada and not tem_principal:
                foto.principal = tem_principal = True
            lugar.fotos.append(foto)
            existentes.add(foto.url)
            novas += 1
            verificadas += int(foto.verificada)
        db.session.commit()
        return novas, verificadas


class CurarFotoService:
    """Curadoria manual (CLI tools/fotos.py): aprovar, rejeitar e escolher a principal."""

    def __init__(self, unsplash=None):
        self.unsplash = unsplash or FotosUnsplashService()

    def _foto(self, foto_id):
        foto = FotoLugar.buscar_por_id(foto_id)
        if foto is None:
            raise NaoEncontrado("Foto não encontrada.")
        return foto

    def aprovar(self, foto_id, criterio="Conferida manualmente pela curadoria"):
        foto = self._foto(foto_id)
        foto.verificada = True
        foto.criterio_verificacao = criterio
        if not any(f.principal and f.verificada for f in foto.lugar.fotos if f.id != foto.id):
            foto.principal = True
        if foto.fonte == "unsplash" and foto.id_externo:
            self.unsplash.registrar_uso(foto.id_externo)
        db.session.commit()
        return foto

    def rejeitar(self, foto_id):
        foto = self._foto(foto_id)
        lugar = foto.lugar
        foto.deletar()
        if lugar.fotos_verificadas and not any(f.principal for f in lugar.fotos_verificadas):
            lugar.fotos_verificadas[0].principal = True
            db.session.commit()

    def definir_principal(self, foto_id):
        foto = self._foto(foto_id)
        if not foto.verificada:
            raise NaoEncontrado("Só uma foto verificada pode ser a principal.")
        for outra in foto.lugar.fotos:
            outra.principal = outra.id == foto.id
        db.session.commit()
        return foto


class ObterFundoInicialService:
    """Fotografia real para o fundo da tela inicial (feature 12).

    Prioridade: versão otimizada local (gerada por `python -m tools.fotos fundo`) →
    melhor foto verificada de paisagem do acervo (miniaturas responsivas do Commons) →
    nenhuma (a página usa o fundo de reserva).
    """

    def executar(self):
        manifesto = os.path.join(PASTA_FUNDO, "fundo.json")
        if os.path.isfile(manifesto):
            try:
                with open(manifesto, encoding="utf-8") as arquivo:
                    dados = json.load(arquivo)
                return {"disponivel": True, "origem": "local", **dados}
            except (OSError, ValueError):
                pass
        foto = self._melhor_foto()
        if foto is None:
            return {"disponivel": False}
        larguras = [w for w in (960, 1600, 2400) if not foto.largura or w <= foto.largura]
        base = foto.url_media or foto.url
        fontes = [{"largura": w, "url": miniatura(base, w) if foto.fonte == "wikimedia" else base} for w in larguras] \
            or [{"largura": foto.largura or 1280, "url": base}]
        return {
            "disponivel": True,
            "origem": "acervo",
            "lugar": {"id": foto.lugar.id, "nome": foto.lugar.nome, "local": f"{foto.lugar.cidade}, {foto.lugar.estado}"},
            "fontes": fontes,
            "credito": {"autor": foto.autor, "licenca": foto.licenca, "licenca_url": foto.licenca_url,
                        "fonte": foto.to_dict()["fonte_nome"], "pagina_origem": foto.pagina_origem},
        }

    @staticmethod
    def _melhor_foto():
        for nome in LUGARES_FUNDO_INICIAL:
            lugar = db.session.query(Lugar).filter(Lugar.nome == nome).first()
            if lugar is None:
                continue
            paisagens = [f for f in lugar.fotos_verificadas
                         if (f.largura or 0) >= 1600 and f.altura and f.largura / f.altura >= 1.3]
            if paisagens:
                return max(paisagens, key=lambda f: (f.principal, f.largura))
        return None


_sincronizando = threading.Lock()


def sincronizar_em_segundo_plano(app):
    """Executa a sincronização Wikimedia numa thread, sem atrasar a subida do servidor."""
    if not _sincronizando.acquire(blocking=False):
        return None

    def tarefa():
        try:
            with app.app_context():
                relatorio = SincronizarFotosService().executar()
                print(f"[Fotos] sincronização concluída: {relatorio['verificadas']} verificadas em "
                      f"{relatorio['lugares']} lugares; {len(relatorio['erros'])} avisos.", flush=True)
        except Exception as erro:  # nunca derruba o app
            print(f"[Fotos] sincronização falhou: {erro}", flush=True)
        finally:
            _sincronizando.release()

    thread = threading.Thread(target=tarefa, name="sincronizar-fotos", daemon=True)
    thread.start()
    return thread


__all__ = ["ListarFotosLugarService", "SincronizarFotosService", "CurarFotoService", "ObterFundoInicialService",
           "sincronizar_em_segundo_plano", "Config"]
