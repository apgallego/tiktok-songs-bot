"""Genera el guion del vídeo con la API gratuita de Gemini (Google AI Studio)."""
import json
import os
import time

import requests

GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
    "gemini-2.5-flash-lite",  # respaldo si el principal está saturado o no existe
]
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # tercer nivel, opcional

PROMPT = """Eres guionista de vídeos cortos (TikTok, Reels, Shorts) sobre música.
Escribe un guion en español sobre la canción "{song}" de {artist}.

Datos de referencia (extractos de Wikipedia). Basa el guion en ellos, parafraseando con tus
palabras; no los copies literalmente:
{contexto}

Reglas:
- La narración debe durar 20-30 segundos leída en voz alta: entre 55 y 75 palabras.
- Estilo de narrador de documental: cuenta una historia, con ritmo y frases de 8-15 palabras.
  Usa comas y puntos para marcar pausas. Nada de listas ni de tono de anuncio.
- Empieza con un gancho potente en la primera frase (una pregunta o un dato sorprendente).
- Cuenta algo de la canción (cómo nació, de qué habla, su impacto) y algo del artista.
- Usa solo datos de los extractos o datos muy conocidos y contrastados. Si dudas, no lo incluyas.
- NO cites la letra de la canción, ni siquiera un verso.
- Termina con una frase corta que invite a comentar o seguir la cuenta.
- Sin emojis ni siglas en la narración; escribe los números con palabras.

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


class _Skip(Exception):
    """El proveedor no puede servir este modelo: pasar al siguiente sin reintentar."""


def _gemini(model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
    }
    r = requests.post(
        url, params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=180
    )
    if r.status_code in (400, 401, 403, 404):
        raise _Skip(f"Gemini {model}: HTTP {r.status_code}")
    r.raise_for_status()  # 429 y 5xx se reintentan
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(model: str, prompt: str) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    if r.status_code in (400, 401, 403, 404):
        raise _Skip(f"Groq {model}: HTTP {r.status_code} {r.text[:300]}")
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def generate_script(song: str, artist: str, context: str = "") -> dict:
    prompt = PROMPT.format(
        song=song, artist=artist,
        contexto=context or "(No hay extractos disponibles: usa solo datos muy conocidos.)",
    )
    chain = [(_gemini, m) for m in GEMINI_MODELS]
    if os.getenv("GROQ_API_KEY"):
        chain.append((_groq, GROQ_MODEL))

    last_err = None
    for fn, model in chain:
        for attempt in range(3):
            try:
                data = json.loads(fn(model, prompt))
                _validate(data)
                return data
            except _Skip as e:
                last_err = e
                print(f"  {e}; paso al siguiente proveedor", flush=True)
                break
            except Exception as e:  # timeouts, 429/5xx, JSON roto: reintenta
                last_err = e
                print(f"  intento {attempt + 1} con {model} falló: {e}", flush=True)
                time.sleep(10 * (attempt + 1))
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
