"""Validações reutilizadas pelos Services (nunca pelas Controllers)."""
import re

from backend.config import Config
from backend.utils.erros import ErroDeValidacao

REGEX_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


def validar_nome(nome):
    nome = (nome or "").strip()
    if len(nome) < 3:
        raise ErroDeValidacao("Informe seu nome completo (mínimo 3 caracteres).", campo="nome")
    if not re.match(r"^[A-Za-zÀ-ÿ'\s.-]+$", nome):
        raise ErroDeValidacao("O nome deve conter apenas letras.", campo="nome")
    return nome


def validar_email(email):
    """Valida o formato do e-mail. Levanta ErroDeValidacao quando inválido."""
    email = (email or "").strip().lower()
    if not email:
        raise ErroDeValidacao("Informe um e-mail.", campo="email")
    if len(email) > 120 or not REGEX_EMAIL.match(email):
        raise ErroDeValidacao("E-mail inválido. Use o formato nome@dominio.com.", campo="email")
    if ".." in email:
        raise ErroDeValidacao("E-mail inválido.", campo="email")
    return email


def validar_senha(senha, confirmacao=None):
    """Senha com no mínimo SENHA_TAMANHO_MINIMO (6) caracteres."""
    senha = senha or ""
    minimo = Config.SENHA_TAMANHO_MINIMO
    if len(senha) < minimo:
        raise ErroDeValidacao(
            f"A senha deve ter no mínimo {minimo} caracteres.", campo="senha"
        )
    if senha.strip() == "":
        raise ErroDeValidacao("A senha não pode conter apenas espaços.", campo="senha")
    if confirmacao is not None and senha != confirmacao:
        raise ErroDeValidacao("As senhas não conferem.", campo="confirmacao_senha")
    return senha


def validar_codigo(codigo):
    codigo = re.sub(r"\D", "", codigo or "")
    if len(codigo) != 6:
        raise ErroDeValidacao("O código deve ter 6 dígitos.", campo="codigo")
    return codigo


def validar_orcamento(orcamento):
    try:
        orcamento = int(orcamento)
    except (TypeError, ValueError):
        raise ErroDeValidacao("Orçamento inválido.", campo="orcamento")
    if orcamento not in (1, 2, 3, 4):
        raise ErroDeValidacao("O orçamento deve estar entre 1 e 4.", campo="orcamento")
    return orcamento


# ---------------------------------------------------------------------------
# Validações genéricas usadas pelas novas funcionalidades (viagens, roteiros...)
# ---------------------------------------------------------------------------
from datetime import date, datetime  # noqa: E402

RE_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def validar_texto(valor, campo, rotulo, minimo=1, maximo=255, obrigatorio=True):
    texto = (valor if isinstance(valor, str) else ("" if valor is None else str(valor))).strip()
    if not texto:
        if obrigatorio:
            raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
        return None
    if len(texto) < minimo:
        raise ErroDeValidacao(f"{rotulo.capitalize()} deve ter ao menos {minimo} caracteres.", campo=campo)
    if len(texto) > maximo:
        raise ErroDeValidacao(f"{rotulo.capitalize()} deve ter no máximo {maximo} caracteres.", campo=campo)
    return texto


def validar_inteiro(valor, campo, rotulo, minimo=None, maximo=None, obrigatorio=True):
    if valor in (None, ""):
        if obrigatorio:
            raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
        return None
    if isinstance(valor, bool):
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválido.", campo=campo)
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErroDeValidacao(f"{rotulo.capitalize()} deve ser um número inteiro.", campo=campo)
    if minimo is not None and numero < minimo:
        raise ErroDeValidacao(f"{rotulo.capitalize()} deve ser no mínimo {minimo}.", campo=campo)
    if maximo is not None and numero > maximo:
        raise ErroDeValidacao(f"{rotulo.capitalize()} deve ser no máximo {maximo}.", campo=campo)
    return numero


def validar_valor_monetario(valor, campo, rotulo, obrigatorio=True, maximo=10_000_000):
    """Converte "1.234,56", "1234.56" ou 1234.56 em centavos (int)."""
    if valor in (None, ""):
        if obrigatorio:
            raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
        return None
    if isinstance(valor, bool):
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválido.", campo=campo)
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = str(valor).strip().replace("R$", "").replace(" ", "")
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            raise ErroDeValidacao(f"{rotulo.capitalize()} inválido.", campo=campo)
    if numero != numero or numero < 0:  # NaN ou negativo
        raise ErroDeValidacao(f"{rotulo.capitalize()} não pode ser negativo.", campo=campo)
    if numero > maximo:
        raise ErroDeValidacao(f"{rotulo.capitalize()} muito alto.", campo=campo)
    return int(round(numero * 100))


def validar_data(valor, campo, rotulo, obrigatorio=True):
    if valor in (None, ""):
        if obrigatorio:
            raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    try:
        return date.fromisoformat(str(valor).strip()[:10])
    except ValueError:
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválida (use AAAA-MM-DD).", campo=campo)


def validar_hora(valor, campo, rotulo, obrigatorio=False):
    if valor in (None, ""):
        if obrigatorio:
            raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
        return None
    texto = str(valor).strip()[:5]
    if not RE_HORA.match(texto):
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválido (use HH:MM).", campo=campo)
    return texto


def validar_data_hora(valor, campo, rotulo):
    if valor in (None, ""):
        raise ErroDeValidacao(f"Informe {rotulo}.", campo=campo)
    try:
        momento = datetime.fromisoformat(str(valor).strip()[:16])
    except ValueError:
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválido (use AAAA-MM-DDTHH:MM).", campo=campo)
    return momento.replace(second=0, microsecond=0, tzinfo=None)


def validar_escolha(valor, opcoes, campo, rotulo, padrao=None):
    if valor in (None, "") and padrao is not None:
        return padrao
    texto = str(valor or "").strip().lower()
    if texto not in opcoes:
        raise ErroDeValidacao(f"{rotulo.capitalize()} inválido.", campo=campo)
    return texto


def validar_coordenadas(latitude, longitude, obrigatorio=False):
    if latitude in (None, "") and longitude in (None, ""):
        if obrigatorio:
            raise ErroDeValidacao("Informe a localização.", campo="latitude")
        return None, None
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        raise ErroDeValidacao("Coordenadas inválidas.", campo="latitude")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or lat != lat or lon != lon:
        raise ErroDeValidacao("Coordenadas fora do intervalo válido.", campo="latitude")
    return round(lat, 6), round(lon, 6)


def validar_booleano(valor):
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("1", "true", "sim", "on", "yes")


def hora_para_minutos(hora):
    if not hora:
        return None
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def minutos_para_hora(minutos):
    minutos = max(0, min(23 * 60 + 59, int(minutos)))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


