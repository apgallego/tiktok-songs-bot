"""Recursos descargados automáticamente para cada canción (APIs gratuitas, sin clave):

- MusicBrainz: busca la grabación y su álbum (release-group) para localizar la portada.
- Cover Art Archive: descarga la portada del álbum.
- Wikipedia: resumen de la canción y del artista, para dar datos verificados al guion.

No descargamos audio ni vídeo de la canción original, ni fotos reales de los artistas
(derechos de autor y CLAUDE.md).
"""
import os
import time
import urllib.parse

import requests

# MusicBrainz pide un User-Agent identificable; no incluimos datos personales.
UA = {"User-Agent": "SongVideoBot/1.0 (automation)"}
# Desactivada por defecto: las portadas suelen ser fotos de los artistas (CLAUDE.md prohíbe
# caras reales) y MusicBrainz no siempre devuelve el álbum correcto. Activar con USE_COVER=1.
USE_COVER = os.getenv("USE_COVER", "0") == "1"


def _get(url: str, **kw) -> requests.Response:
    return requests.get(url, headers=UA, timeout=30, **kw)


def find_release_group(song: str, artist: str) -> str | None:
    """Devuelve el MBID del álbum (release-group) más probable para la canción."""
    query = f'recording:"{song}" AND artist:"{artist}"'
    try:
        r = _get("https://musicbrainz.org/ws/2/recording/",
                 params={"query": query, "fmt": "json", "limit": 5})
        r.raise_for_status()
        time.sleep(1.1)  # MusicBrainz: máximo ~1 petición por segundo
        for rec in r.json().get("recordings", []):
            for rel in rec.get("releases", []):
                rg = rel.get("release-group", {}).get("id")
                if rg:
                    return rg
    except Exception as e:
        print(f"  MusicBrainz falló: {e}")
    return None


def fetch_cover(song: str, artist: str, out_path: str) -> str | None:
    """Descarga la portada del álbum. Devuelve la ruta o None si no hay."""
    if not USE_COVER:
        return None
    rg = find_release_group(song, artist)
    if not rg:
        print("  Sin portada encontrada en MusicBrainz")
        return None
    try:
        r = _get(f"https://coverartarchive.org/release-group/{rg}/front-1200")
        if r.status_code == 404:
            print("  Cover Art Archive no tiene portada para este álbum")
            return None
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return out_path
    except Exception as e:
        print(f"  Descarga de portada falló: {e}")
        return None


def _wiki_summary(title: str, lang: str) -> str:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    r = _get(url)
    if r.status_code != 200:
        return ""
    return r.json().get("extract", "") or ""


def _first_summary(titles: list) -> str:
    """Primer resumen que exista, probando primero en español y luego en inglés."""
    for title in titles:
        for lang in ("es", "en"):
            try:
                text = _wiki_summary(title, lang)
            except Exception:
                text = ""
            if text:
                return text[:1200]
    return ""


def wiki_context(song: str, artist: str) -> str:
    """Resúmenes de Wikipedia de la canción y del artista, como datos para el guion."""
    parts = []
    song_text = _first_summary([f"{song} (canción)", song])
    if song_text:
        parts.append(f"Canción: {song_text}")
    artist_text = _first_summary([artist])
    if artist_text:
        parts.append(f"Artista: {artist_text}")
    return "\n".join(parts)
