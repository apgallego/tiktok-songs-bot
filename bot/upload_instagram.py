"""Publica un Reel con la API de Instagram (login de Instagram, gratis).
Instagram descarga el vídeo desde una URL pública: usamos una "release" del propio
repositorio de GitHub como alojamiento gratuito."""
import datetime as dt
import os
import time

import requests

from secrets_store import save_secret

GRAPH = "https://graph.instagram.com/v22.0"


def enabled() -> bool:
    return bool(os.getenv("IG_ACCESS_TOKEN") and os.getenv("IG_USER_ID"))


def refresh_token_if_due() -> None:
    """Los tokens de Instagram duran 60 días; lo renovamos cada lunes."""
    if dt.date.today().weekday() != 0:
        return
    r = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_ACCESS_TOKEN"]},
        timeout=30,
    )
    if r.ok and r.json().get("access_token"):
        new = r.json()["access_token"]
        os.environ["IG_ACCESS_TOKEN"] = new
        save_secret("IG_ACCESS_TOKEN", new)
    else:
        print(f"  No se pudo renovar el token de Instagram: {r.text[:200]}")


def host_on_github(video_path: str, tag: str) -> str:
    """Sube el MP4 como asset de una release y devuelve su URL pública."""
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{repo}"
    r = requests.post(f"{api}/releases", headers=h, timeout=30,
                      json={"tag_name": tag, "name": tag, "body": "Vídeo generado automáticamente"})
    if r.status_code == 422:  # ya existe
        r = requests.get(f"{api}/releases/tags/{tag}", headers=h, timeout=30)
    r.raise_for_status()
    upload_url = r.json()["upload_url"].split("{")[0]
    with open(video_path, "rb") as f:
        a = requests.post(upload_url, params={"name": "video.mp4"}, data=f, timeout=300,
                          headers={**h, "Content-Type": "video/mp4"})
    if a.status_code == 422:  # el asset ya estaba subido
        assets = requests.get(f"{api}/releases/tags/{tag}", headers=h, timeout=30).json()["assets"]
        return assets[0]["browser_download_url"]
    a.raise_for_status()
    _cleanup_old_releases(api, h, keep=7)
    return a.json()["browser_download_url"]


def _cleanup_old_releases(api: str, h: dict, keep: int) -> None:
    rels = requests.get(f"{api}/releases", headers=h, params={"per_page": 100}, timeout=30).json()
    vids = sorted([x for x in rels if x["tag_name"].startswith("video-")],
                  key=lambda x: x["created_at"], reverse=True)
    for old in vids[keep:]:
        requests.delete(f"{api}/releases/{old['id']}", headers=h, timeout=30)
        requests.delete(f"{api}/git/refs/tags/{old['tag_name']}", headers=h, timeout=30)


def upload(video_path: str, caption: str, tag: str) -> str:
    refresh_token_if_due()
    token, user = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
    video_url = host_on_github(video_path, tag)
    # resolvemos la redirección para darle a Instagram la URL directa del fichero
    final_url = requests.head(video_url, allow_redirects=True, timeout=30).url

    r = requests.post(f"{GRAPH}/{user}/media", timeout=60, data={
        "media_type": "REELS", "video_url": final_url, "caption": caption[:2200],
        "share_to_feed": "true", "access_token": token,
    })
    r.raise_for_status()
    container = r.json()["id"]

    for _ in range(60):  # espera hasta 10 min a que Instagram procese el vídeo
        s = requests.get(f"{GRAPH}/{container}", timeout=30,
                         params={"fields": "status_code,status", "access_token": token}).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram no pudo procesar el vídeo: {s}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram tardó demasiado en procesar el vídeo")

    p = requests.post(f"{GRAPH}/{user}/media_publish", timeout=60,
                      data={"creation_id": container, "access_token": token})
    p.raise_for_status()
    return f"Instagram media id {p.json()['id']}"
