"""Curadoria das fotografias reais dos lugares e do fundo da tela inicial.

Uso (na raiz do projeto, com acesso à internet):

    python -m tools.fotos sincronizar [--todos] [--fonte wikimedia|pexels|unsplash] [--lugar ID ...]
    python -m tools.fotos listar [--pendentes] [--lugar ID]
    python -m tools.fotos aprovar FOTO_ID [FOTO_ID ...]
    python -m tools.fotos rejeitar FOTO_ID [FOTO_ID ...]
    python -m tools.fotos principal FOTO_ID
    python -m tools.fotos fundo [--foto FOTO_ID]

- "sincronizar" com Wikimedia grava fotos já VERIFICADAS (critérios de coordenadas e nome);
  Pexels/Unsplash gravam candidatas NÃO verificadas, que só aparecem após "aprovar".
- "fundo" baixa a foto escolhida (ou a melhor paisagem verificada), gera versões otimizadas
  (WebP + JPEG em 960/1600/2400 px e um recorte vertical para celulares) em
  frontend/assets/fundo/ e grava fundo.json com a atribuição exigida pela licença.
"""
import argparse
import io
import json
import os
import sys

import requests

from backend.app import create_app
from backend.config import Config
from backend.extensions import db
from backend.models.foto_lugar import FotoLugar
from backend.services.fotos_lugar_service import (
    PASTA_FUNDO,
    CurarFotoService,
    ObterFundoInicialService,
    SincronizarFotosService,
)

LARGURAS_PAISAGEM = (960, 1600, 2400)
LARGURAS_RETRATO = (720, 1080)


def gerar_versoes_fundo(conteudo, pasta, prefixo="fundo"):
    """Recorta/redimensiona a imagem original. Devolve (fontes, fontes_retrato)."""
    from PIL import Image, ImageOps

    os.makedirs(pasta, exist_ok=True)
    imagem = ImageOps.exif_transpose(Image.open(io.BytesIO(conteudo))).convert("RGB")
    fontes, retrato = [], []
    for largura in LARGURAS_PAISAGEM:
        if largura > imagem.width:
            continue
        altura = round(imagem.height * largura / imagem.width)
        versao = imagem.resize((largura, altura), Image.LANCZOS)
        for formato, extensao, opcoes in (("WEBP", "webp", {"quality": 78, "method": 6}),
                                          ("JPEG", "jpg", {"quality": 80, "optimize": True, "progressive": True})):
            nome = f"{prefixo}-{largura}.{extensao}"
            versao.save(os.path.join(pasta, nome), formato, **opcoes)
        fontes.append({"largura": largura, "url": f"assets/fundo/{prefixo}-{largura}.webp",
                       "url_jpg": f"assets/fundo/{prefixo}-{largura}.jpg"})
    # Recorte vertical (9:16) centrado, para telas em pé
    alvo = 9 / 16
    largura_corte = min(imagem.width, round(imagem.height * alvo))
    esquerda = (imagem.width - largura_corte) // 2
    vertical = imagem.crop((esquerda, 0, esquerda + largura_corte, imagem.height))
    for largura in LARGURAS_RETRATO:
        if largura > vertical.width:
            continue
        versao = vertical.resize((largura, round(largura / alvo)), Image.LANCZOS)
        nome = f"{prefixo}-retrato-{largura}.webp"
        versao.save(os.path.join(pasta, nome), "WEBP", quality=78, method=6)
        retrato.append({"largura": largura, "url": f"assets/fundo/{nome}"})
    if not fontes:  # imagem pequena: usa o tamanho original
        nome = f"{prefixo}-{imagem.width}.jpg"
        imagem.save(os.path.join(pasta, nome), "JPEG", quality=82, optimize=True, progressive=True)
        fontes.append({"largura": imagem.width, "url": f"assets/fundo/{nome}"})
    return fontes, retrato


def comando_sincronizar(args):
    relatorio = SincronizarFotosService().executar(
        lugar_ids=args.lugar, fontes=(args.fonte,), somente_sem_fotos=not args.todos)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))


def comando_listar(args):
    consulta = db.session.query(FotoLugar)
    if args.pendentes:
        consulta = consulta.filter(FotoLugar.verificada.is_(False))
    if args.lugar:
        consulta = consulta.filter(FotoLugar.lugar_id.in_(args.lugar))
    for foto in consulta.order_by(FotoLugar.lugar_id, FotoLugar.ordem).all():
        estado = "✓" if foto.verificada else "?"
        principal = "★" if foto.principal else " "
        print(f"{estado}{principal} #{foto.id:<4} [{foto.fonte}] {foto.lugar.nome}: {foto.titulo or ''}\n"
              f"        {foto.url}\n        {foto.autor} · {foto.licenca} · {foto.criterio_verificacao or ''}")


def comando_fundo(args):
    if args.foto:
        foto = FotoLugar.buscar_por_id(args.foto)
        if foto is None or not foto.verificada:
            sys.exit("Escolha uma foto verificada (veja 'listar').")
    else:
        foto = ObterFundoInicialService._melhor_foto()
        if foto is None:
            sys.exit("Nenhuma paisagem verificada com ≥1600 px. Rode 'sincronizar' primeiro.")
    url = foto.url_original or foto.url
    print(f"Baixando {url}")
    resposta = requests.get(url, headers={"User-Agent": Config.HTTP_USER_AGENT}, timeout=60)
    resposta.raise_for_status()
    fontes, retrato = gerar_versoes_fundo(resposta.content, PASTA_FUNDO)
    manifesto = {
        "lugar": {"id": foto.lugar.id, "nome": foto.lugar.nome, "local": f"{foto.lugar.cidade}, {foto.lugar.estado}"},
        "fontes": fontes,
        "fontes_retrato": retrato,
        "credito": {"autor": foto.autor, "licenca": foto.licenca, "licenca_url": foto.licenca_url,
                    "fonte": foto.to_dict()["fonte_nome"], "pagina_origem": foto.pagina_origem},
    }
    with open(os.path.join(PASTA_FUNDO, "fundo.json"), "w", encoding="utf-8") as arquivo:
        json.dump(manifesto, arquivo, ensure_ascii=False, indent=2)
    print(f"Fundo gerado em {PASTA_FUNDO} ({len(fontes)} paisagem, {len(retrato)} retrato).")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Curadoria das fotografias do Viajaí")
    sub = parser.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("sincronizar")
    s.add_argument("--fonte", default="wikimedia", choices=("wikimedia", "pexels", "unsplash"))
    s.add_argument("--lugar", type=int, nargs="*")
    s.add_argument("--todos", action="store_true", help="inclui lugares que já têm foto")
    lst = sub.add_parser("listar")
    lst.add_argument("--pendentes", action="store_true")
    lst.add_argument("--lugar", type=int, nargs="*")
    for nome in ("aprovar", "rejeitar"):
        sub.add_parser(nome).add_argument("ids", type=int, nargs="+")
    sub.add_parser("principal").add_argument("id", type=int)
    sub.add_parser("fundo").add_argument("--foto", type=int)
    args = parser.parse_args(argv)

    Config.FOTOS_SINCRONIZACAO_AUTOMATICA = False  # o CLI faz a sincronização explicitamente
    app = create_app()
    with app.app_context():
        curadoria = CurarFotoService()
        if args.comando == "sincronizar":
            comando_sincronizar(args)
        elif args.comando == "listar":
            comando_listar(args)
        elif args.comando == "aprovar":
            for foto_id in args.ids:
                print(f"Aprovada #{curadoria.aprovar(foto_id).id}")
        elif args.comando == "rejeitar":
            for foto_id in args.ids:
                curadoria.rejeitar(foto_id)
                print(f"Removida #{foto_id}")
        elif args.comando == "principal":
            print(f"Principal: #{curadoria.definir_principal(args.id).id}")
        elif args.comando == "fundo":
            comando_fundo(args)


if __name__ == "__main__":
    main()
