"""Genera el guion del vídeo con la API gratuita de Gemini (Google AI Studio)."""
import json
import os
import time

import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PROMPT = """Eres guionista de vídeos cortos (TikTok, Reels, Shorts) sobre música.
Escribe un guion en español sobre la canción "{song}" de {artist}.

Reglas:
- La narración debe durar 20-30 segundos leída en voz alta: entre 55 y 75 palabras.
- Empieza con un gancho potente en la primera frase (una pregunta o un dato sorprendente).
- Cuenta algo de la canción (cómo nació, de qué habla, su impacto) y algo del artista.
- Usa solo datos muy conocidos y contrastados. Si dudas de un dato, no lo incluyas.
- NO cites la letra de la canción, ni siquiera un verso.
- Termina con una frase corta que invite a comentar o seguir la cuenta.
- Frases cortas y naturales, pensadas para escucharse, sin emojis en la narración.

Además genera 4 descripciones de imágenes EN INGLÉS para ilustrar el vídeo (una por cada parte
de la narración, en orden). Deben ser ilustraciones artísticas que evoquen la época, el lugar o
el ambiente de la canción. No describas a personas reales ni sus caras; usa escenas, objetos,
instrumentos, siluetas o paisajes. Estilo coherente entre ellas.

Devuelve SOLO un JSON con esta forma:
{{
  "titulo": "texto corto para mostrar arriba del vídeo (máx. 40 caracteres)",
  "narracion": "texto completo que se leerá en voz alta",
  "imagenes": ["prompt 1", "prompt 2", "prompt 3", "prompt 4"],
  "descripcion": "texto para la publicación (1-2 frases, puede llevar emojis)",
  "hashtags": ["#musica", "..."]
}}
"""


def generate_script(song: str, artist: str) -> dict:
    api_key = os.environ["GEMINI_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(song=song, artist=artist)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.post(url, params={"key": api_key}, json=body, timeout=180)
            if r.status_code in (429, 500, 503):
                raise RuntimeError(f"Gemini {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            _validate(data)
            return data
        except Exception as e:  # reintenta ante límites o JSON roto
            last_err = e
            time.sleep(15 * (attempt + 1))
    raise RuntimeError(f"No se pudo generar el guion: {last_err}")


def _validate(d: dict) -> None:
    for key in ("titulo", "narracion", "imagenes", "descripcion", "hashtags"):
        if key not in d:
            raise ValueError(f"Falta '{key}' en la respuesta de Gemini")
    if not d["imagenes"]:
        raise ValueError("Gemini no devolvió prompts de imagen")
    words = len(d["narracion"].split())
    if words < 35 or words > 110:
        raise ValueError(f"Narración con longitud rara ({words} palabras)")
