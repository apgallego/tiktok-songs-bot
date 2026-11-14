"""Imágenes gratuitas con Pollinations.ai. Si falla, crea un fondo degradado."""
import hashlib
import io
import random
import time
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
STYLE = ", vertical poster, cinematic lighting, rich colors, detailed digital illustration, no text, no letters"


def fetch_image(prompt: str, out_path: str, seed: int) -> None:
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + STYLE)
    params = {"width": W, "height": H, "nologo": "true", "seed": seed, "model": "flux"}
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            cover(img).save(out_path, quality=92)
            return
        except Exception as e:
            print(f"  Pollinations falló ({e}); reintento {attempt + 1}/3")
            time.sleep(10 * (attempt + 1))
    print("  Usando fondo degradado de reserva")
    gradient(prompt, out_path)


def cover(img: Image.Image) -> Image.Image:
    """Recorta/escala la imagen para que llene 1080x1920."""
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def cover_card(cover_path: str, out_path: str) -> str:
    """Portada del álbum centrada sobre su propia versión difuminada (1080x1920)."""
    src = Image.open(cover_path).convert("RGB")
    bg = cover(src).filter(ImageFilter.GaussianBlur(40))
    side = 880
    art = src.copy()
    scale = side / min(art.width, art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.LANCZOS)
    left, top = (art.width - side) // 2, (art.height - side) // 2
    art = art.crop((left, top, left + side, top + side))
    # sombra suave bajo la portada
    shadow = Image.new("RGBA", (side + 60, side + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([30, 30, side + 30, side + 30], fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas = bg.convert("RGBA")
    px, py = (W - side) // 2, (H - side) // 2 - 120
    canvas.alpha_composite(shadow, (px - 30, py - 30))
    canvas.paste(art, (px, py))
    canvas.convert("RGB").save(out_path, quality=92)
    return out_path


def gradient(seed_text: str, out_path: str) -> None:
    rnd = random.Random(hashlib.md5(seed_text.encode()).hexdigest())
    c1 = [rnd.randint(20, 120) for _ in range(3)]
    c2 = [rnd.randint(100, 255) for _ in range(3)]
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    for _ in range(14):  # unos círculos difuminados para que no quede plano
        r = rnd.randint(80, 320)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=tuple(rnd.randint(60, 255) for _ in range(3)))
    img.filter(ImageFilter.GaussianBlur(60)).save(out_path, quality=92)
