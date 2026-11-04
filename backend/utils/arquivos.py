"""Uploads de fotografias: validação, normalização e URLs assinadas.

- Aceita apenas JPEG, PNG e WebP (confere a assinatura binária, não só a extensão).
- Recodifica com Pillow: remove metadados EXIF (inclusive GPS), corrige a orientação
  e limita o tamanho — protegendo a privacidade de quem envia.
- Os arquivos ficam fora da pasta pública e só são servidos por URL assinada (HMAC)
  com validade, gerada pelo backend depois de checar a permissão de quem lista.
"""
import hashlib
import hmac
import io
import os
import re
import secrets
import time

from backend.config import Config
from backend.utils.erros import ErroDeValidacao

try:  # Pillow é recomendado (requirements.txt); sem ele só a assinatura binária é checada.
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 40_000_000  # evita "bombas de descompressão"
except ImportError:  # pragma: no cover
    Image = None

SUBPASTAS = ("avaliacoes", "diario")
RE_NOME = re.compile(r"^[a-f0-9]{32}\.(jpg|png|webp)$")

ASSINATURAS = {
    "jpg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),
}


def _detectar_formato(cabecalho):
    if cabecalho.startswith(ASSINATURAS["jpg"][0]):
        return "jpg"
    if cabecalho.startswith(ASSINATURAS["png"][0]):
        return "png"
    if cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP":
        return "webp"
    return None


def pasta(subpasta, config=Config):
    if subpasta not in SUBPASTAS:
        raise ValueError("subpasta inválida")
    caminho = os.path.join(config.PASTA_UPLOADS, subpasta)
    os.makedirs(caminho, exist_ok=True)
    return caminho


def salvar_imagem(arquivo, subpasta, config=Config):
    """Valida e grava um FileStorage do Flask. Devolve o nome gerado."""
    if arquivo is None or not getattr(arquivo, "filename", ""):
        raise ErroDeValidacao("Selecione uma imagem.", campo="fotos")
    dados = arquivo.read(config.UPLOAD_TAMANHO_MAXIMO_MB * 1024 * 1024 + 1)
    if len(dados) > config.UPLOAD_TAMANHO_MAXIMO_MB * 1024 * 1024:
        raise ErroDeValidacao(
            f"Cada foto pode ter no máximo {config.UPLOAD_TAMANHO_MAXIMO_MB} MB.", campo="fotos"
        )
    if len(dados) < 32:
        raise ErroDeValidacao("Arquivo de imagem inválido.", campo="fotos")
    formato = _detectar_formato(dados[:16])
    if formato is None:
        raise ErroDeValidacao("Formato não suportado. Envie JPG, PNG ou WebP.", campo="fotos")

    if Image is not None:
        try:
            imagem = Image.open(io.BytesIO(dados))
            imagem.verify()  # detecta arquivos corrompidos/forjados
            imagem = Image.open(io.BytesIO(dados))
            imagem = ImageOps.exif_transpose(imagem)
            lado = config.UPLOAD_LADO_MAXIMO_PX
            imagem.thumbnail((lado, lado))
            saida = io.BytesIO()
            if formato == "png" and imagem.mode in ("RGBA", "LA", "P"):
                imagem.save(saida, "PNG", optimize=True)
            else:
                formato = "jpg"
                imagem.convert("RGB").save(saida, "JPEG", quality=84, optimize=True, progressive=True)
            dados = saida.getvalue()  # sem EXIF/GPS: nenhum metadado é copiado
        except ErroDeValidacao:
            raise
        except Exception:
            raise ErroDeValidacao("Não foi possível ler a imagem enviada.", campo="fotos")

    nome = f"{secrets.token_hex(16)}.{formato}"
    with open(os.path.join(pasta(subpasta, config), nome), "wb") as destino:
        destino.write(dados)
    return nome


def remover_imagem(subpasta, nome, config=Config):
    if not nome or not RE_NOME.match(nome):
        return
    caminho = os.path.join(pasta(subpasta, config), nome)
    if os.path.isfile(caminho):
        os.remove(caminho)


# ---------------------------------------------------------------------------
# URLs assinadas
# ---------------------------------------------------------------------------
def _assinatura(subpasta, nome, expira, chave):
    mensagem = f"{subpasta}/{nome}:{expira}".encode()
    return hmac.new(chave.encode(), mensagem, hashlib.sha256).hexdigest()[:40]


def url_assinada(subpasta, nome, config=Config):
    expira = int(time.time()) + config.URL_ARQUIVO_VALIDADE_MINUTOS * 60
    # Arredonda para a hora: URLs estáveis aproveitam o cache do navegador.
    expira = expira - expira % 3600 + 3600
    assinatura = _assinatura(subpasta, nome, expira, config.SECRET_KEY)
    return f"/api/arquivos/{subpasta}/{nome}?exp={expira}&sig={assinatura}"


def assinatura_valida(subpasta, nome, expira, assinatura, config=Config):
    if subpasta not in SUBPASTAS or not RE_NOME.match(nome or ""):
        return False
    try:
        expira = int(expira)
    except (TypeError, ValueError):
        return False
    if expira < time.time():
        return False
    esperado = _assinatura(subpasta, nome, expira, config.SECRET_KEY)
    return hmac.compare_digest(esperado, assinatura or "")
