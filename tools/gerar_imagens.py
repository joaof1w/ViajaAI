"""Gera as imagens de fundo/cartões do app (praia ao pôr do sol, gastronomia, etc.).

Executado uma única vez para produzir os arquivos em frontend/assets/.
"""
import os

import numpy as np
from PIL import Image, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "assets")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def fbm(h, w, octaves=6, base=4, gain=0.5, seed=1):
    r = np.random.default_rng(seed)
    total = np.zeros((h, w), dtype=np.float32)
    amp, freq = 1.0, base
    norm = 0.0
    for _ in range(octaves):
        gh, gw = max(2, int(freq)), max(2, int(freq * w / h))
        grid = r.random((gh, gw)).astype(np.float32)
        layer = np.array(Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0
        total += layer * amp
        norm += amp
        amp *= gain
        freq *= 2
    total /= norm
    return (total - total.min()) / (total.max() - total.min() + 1e-6)


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def praia_por_do_sol(w=1080, h=1920):
    y = np.linspace(0, 1, h, dtype=np.float32)
    x = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(x, y)

    horizonte = 0.46
    img = np.zeros((h, w, 3), dtype=np.float32)

    # ---------------- céu ----------------
    ceu = Y / horizonte
    ceu = np.clip(ceu, 0, 1)
    topo = np.array([0.24, 0.52, 0.68])        # azul esverdeado
    meio = np.array([0.72, 0.66, 0.68])        # cinza rosado
    baixo = np.array([1.00, 0.72, 0.44])       # laranja quente
    t1 = np.clip(ceu / 0.62, 0, 1) ** 1.15
    t2 = np.clip((ceu - 0.62) / 0.38, 0, 1) ** 0.85
    ceu_rgb = lerp(topo, meio, t1)
    ceu_rgb = lerp(ceu_rgb, baixo, t2)

    # brilho do sol logo acima do horizonte, à esquerda
    sx, sy = 0.22, horizonte - 0.03
    d = np.sqrt(((X - sx) * 1.35) ** 2 + (Y - sy) ** 2)
    glow = np.exp(-(d / 0.34) ** 1.6)
    ceu_rgb += glow[..., None] * np.array([0.62, 0.38, 0.14])

    # nuvens
    n = fbm(h, w, octaves=7, base=3, seed=11)
    faixa = np.exp(-((Y - 0.22) / 0.17) ** 2) * 1.0 + np.exp(-((Y - 0.38) / 0.09) ** 2) * 0.75
    nuvem = np.clip((n - 0.44) * 4.2, 0, 1) * faixa
    nuvem = np.array(Image.fromarray((nuvem * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), dtype=np.float32) / 255.0
    cor_nuvem = lerp(np.array([0.99, 0.82, 0.70]), np.array([1.0, 0.95, 0.90]), np.clip(1 - Y / horizonte, 0, 1))
    ceu_rgb = ceu_rgb * (1 - nuvem[..., None] * 0.85) + cor_nuvem * (nuvem[..., None] * 0.85)

    # ---------------- mar ----------------
    mar_t = np.clip((Y - horizonte) / (1 - horizonte), 0, 1)
    long_e = np.array([0.06, 0.34, 0.44])      # turquesa profundo (perto do horizonte)
    medio = np.array([0.10, 0.64, 0.68])       # turquesa claro
    raso = np.array([0.47, 0.86, 0.83])        # água rasa
    mar_rgb = lerp(long_e, medio, np.clip(mar_t / 0.45, 0, 1))
    mar_rgb = lerp(mar_rgb, raso, np.clip((mar_t - 0.45) / 0.55, 0, 1) ** 1.3)

    # ondulação (frequência cresce com a perspectiva: mais fina perto do horizonte)
    onda = fbm(h, w, octaves=6, base=5, seed=23)
    onda2 = fbm(h, w, octaves=4, base=3, seed=41)
    freq = 12 + 30 * (1 - mar_t) ** 2
    ripple = np.sin(mar_t * freq * 6 + onda * 11 + onda2 * 7) * 0.5 + 0.5
    ripple *= np.clip(mar_t * 3.2, 0, 1)  # some no horizonte
    mar_rgb += (ripple * (0.010 + 0.050 * mar_t))[..., None] * np.array([0.9, 1.0, 1.0])

    # reflexo dourado do sol na água
    refl = np.exp(-(((X - sx) * 2.2) ** 2)) * np.exp(-((Y - horizonte) / 0.30) ** 2)
    refl *= (0.45 + 0.55 * ripple)
    mar_rgb += refl[..., None] * np.array([0.85, 0.58, 0.26])

    # linhas de espuma / rebentação (mais largas conforme se aproximam da areia)
    for cy, esp, forca in ((0.585, 0.006, 0.35), (0.665, 0.011, 0.55), (0.775, 0.020, 0.80), (0.905, 0.042, 1.0)):
        dist = fbm(h, w, octaves=5, base=4, seed=int(cy * 1000)) * (0.010 + 0.055 * cy)
        banda = np.exp(-((Y - cy + dist) / esp) ** 2) * forca
        mar_rgb = mar_rgb * (1 - banda[..., None]) + np.array([0.97, 0.99, 0.99]) * banda[..., None]

    # areia molhada refletindo o céu no rodapé
    areia = np.clip((Y - 0.93) / 0.07, 0, 1)
    cor_areia = np.array([0.86, 0.83, 0.79])
    mar_rgb = lerp(mar_rgb, cor_areia, areia * 0.75)

    img = np.where((Y < horizonte)[..., None], ceu_rgb, mar_rgb)

    # neblina atmosférica dissolvendo a linha do horizonte
    haze = np.exp(-((Y - horizonte) / 0.035) ** 2)
    cor_haze = np.array([0.95, 0.82, 0.68]) * (0.55 + 0.45 * glow)[..., None]
    img = img * (1 - (haze * 0.42)[..., None]) + cor_haze * (haze * 0.42)[..., None]

    # vinheta suave + grão
    vin = 1 - 0.30 * (((X - 0.5) * 1.7) ** 2 + ((Y - 0.5) * 1.2) ** 2)
    img *= np.clip(vin, 0, 1)[..., None]
    img += rng.normal(0, 0.008, img.shape)

    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    out = out.filter(ImageFilter.GaussianBlur(0.6))
    out.save(os.path.join(OUT, "praia.jpg"), quality=88)
    return out


def cartao(nome, cores, seed, textura="suave"):
    """Imagem abstrata para os cartões de destino (720x480)."""
    w, h = 720, 480
    y = np.linspace(0, 1, h, dtype=np.float32)
    x = np.linspace(0, 1, w, dtype=np.float32)
    X, Y = np.meshgrid(x, y)
    a, b, c = [np.array(k, dtype=np.float32) / 255 for k in cores]
    t = np.clip(Y * 0.7 + X * 0.3, 0, 1)
    img = lerp(a, b, np.clip(t / 0.55, 0, 1))
    img = lerp(img, c, np.clip((t - 0.55) / 0.45, 0, 1))
    n = fbm(h, w, octaves=6, base=4, seed=seed)
    if textura == "ondas":
        img += (np.sin(Y * 26 + n * 5) * 0.5 + 0.5)[..., None] * 0.09
    elif textura == "manchas":
        img += (np.clip((n - 0.5) * 2.2, 0, 1))[..., None] * 0.16
    else:
        img += (n - 0.5)[..., None] * 0.13
    vin = 1 - 0.25 * (((X - 0.5) * 1.5) ** 2 + ((Y - 0.5) * 1.3) ** 2)
    img *= np.clip(vin, 0, 1)[..., None]
    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out.save(os.path.join(OUT, f"{nome}.jpg"), quality=85)


if __name__ == "__main__":
    praia_por_do_sol()
    cartao("card-praia", [(35, 120, 140), (60, 190, 190), (200, 235, 230)], 3, "ondas")
    cartao("card-gastronomia", [(60, 25, 20), (150, 70, 40), (235, 170, 95)], 5, "manchas")
    cartao("card-aventura", [(20, 60, 45), (55, 120, 80), (170, 205, 140)], 9, "suave")
    cartao("card-cultura", [(45, 30, 70), (110, 75, 150), (225, 200, 235)], 13, "suave")
    cartao("card-natureza", [(15, 65, 55), (45, 140, 105), (185, 225, 180)], 17, "manchas")
    cartao("card-museus", [(70, 55, 25), (165, 130, 60), (240, 220, 170)], 21, "suave")
    print("imagens geradas em", OUT)
