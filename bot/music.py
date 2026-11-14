"""Música de fondo libre, descargada de Wikimedia Commons.

Solo se aceptan licencias que permiten usarla en vídeos comerciales sin contagiar la licencia
(CC0, dominio público y CC BY, que exige crédito). Se descartan CC BY-SA, himnos y canciones
con voz. Cada pista descargada se guarda con su crédito para la descripción del vídeo.
"""
import os
import random
import re
import time

import requests

UA = {"User-Agent": "SongVideoBot/1.0 (automation)"}
API = "https://commons.wikimedia.org/w/api.php"
QUERIES = ["ambient music", "ambient piano", "piano solo", "ambient electronic"]
ALLOWED = ("CC0", "Public domain", "CC BY 3.0", "CC BY 4.0", "CC BY 2.0", "CC BY 2.5")
EXCLUDE = re.compile(r"anthem|hymn|lied|march|vocal|sing|lyric|song|feat|rap|rock|\bnational\b",
                     re.I)
MAX_BYTES = 12 * 1024 * 1024
AUDIO_EXT = (".ogg", ".oga", ".opus", ".mp3", ".wav", ".flac", ".m4a")  # no MIDI: no es audio


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _get_retry(url: str, **kw) -> requests.Response:
    """GET con espera y reintento ante 429 (límite de Commons)."""
    for attempt in range(4):
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    return r


def _candidates() -> list:
    found = {}
    for q in QUERIES:
        try:
            r = _get_retry(API, params={
                "action": "query", "format": "json", "generator": "search",
                "gsrnamespace": 6, "gsrsearch": f"filetype:audio {q}", "gsrlimit": 15,
                "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
                "iiextmetadatafilter": "LicenseShortName|Artist|ObjectName",
            })
            pages = r.json().get("query", {}).get("pages", {}).values()
        except Exception as e:
            print(f"  Commons búsqueda '{q}' falló: {e}")
            continue
        for p in pages:
            info = (p.get("imageinfo") or [{}])[0]
            em = info.get("extmetadata", {})
            lic = _strip_html(em.get("LicenseShortName", {}).get("value", ""))
            title = p.get("title", "")
            if not lic.startswith(ALLOWED) or EXCLUDE.search(title):
                continue
            if info.get("size", 0) > MAX_BYTES or not title.lower().endswith(AUDIO_EXT):
                continue
            found[title] = {
                "title": title.replace("File:", "", 1),
                "url": info["url"],
                "license": lic,
                "artist": _strip_html(em.get("Artist", {}).get("value", "")) or "desconocido",
            }
    return list(found.values())


def fetch_background(out_dir: str) -> dict | None:
    """Descarga una pista de fondo al azar. Devuelve {path, title, artist, license} o None."""
    cands = _candidates()
    random.shuffle(cands)
    for c in cands[:5]:
        try:
            r = _get_retry(c["url"])
            ext = os.path.splitext(c["title"])[1].lower() or ".ogg"
            path = os.path.join(out_dir, "bg" + ext)
            with open(path, "wb") as f:
                f.write(r.content)
            return {**c, "path": path}
        except Exception as e:
            print(f"  Descarga de música falló ({c['title']}): {e}")
    return None
