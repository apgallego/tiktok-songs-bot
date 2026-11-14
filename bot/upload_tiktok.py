"""Sube el vídeo a TikTok con la Content Posting API (gratis).

Modo por defecto: "inbox" -> el vídeo llega como borrador a tu app de TikTok y lo publicas
con un toque (funciona sin que TikTok haya auditado tu app).
Cuando TikTok apruebe tu app, pon la variable TIKTOK_MODE=direct para publicar del tirón.
"""
import math
import os
import time

import requests

from secrets_store import save_secret

API = "https://open.tiktokapis.com/v2"


def enabled() -> bool:
    return all(os.getenv(k) for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"))


def _access_token() -> str:
    r = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"No se pudo renovar el token de TikTok: {data}")
    new_refresh = data.get("refresh_token")
    if new_refresh and new_refresh != os.environ["TIKTOK_REFRESH_TOKEN"]:
        save_secret("TIKTOK_REFRESH_TOKEN", new_refresh)
    return data["access_token"]


def upload(video_path: str, caption: str) -> str:
    token = _access_token()
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    size = os.path.getsize(video_path)
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    n_chunks = math.ceil(size / chunk) if size > chunk else 1
    source = {"source": "FILE_UPLOAD", "video_size": size,
              "chunk_size": chunk, "total_chunk_count": n_chunks}

    if os.getenv("TIKTOK_MODE", "inbox") == "direct":
        body = {"post_info": {"title": caption[:2200],
                              "privacy_level": os.getenv("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE"),
                              "disable_comment": False, "is_aigc": True},
                "source_info": source}
        url = f"{API}/post/publish/video/init/"
    else:
        body = {"source_info": source}
        url = f"{API}/post/publish/inbox/video/init/"

    r = requests.post(url, headers=h, json=body, timeout=60)
    data = r.json()
    if data.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok init falló: {data}")
    publish_id, upload_url = data["data"]["publish_id"], data["data"]["upload_url"]

    with open(video_path, "rb") as f:
        for i in range(n_chunks):
            part = f.read(chunk if i < n_chunks - 1 else size)
            start = i * chunk
            end = start + len(part) - 1
            u = requests.put(upload_url, data=part, timeout=300, headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Content-Length": str(len(part)),
            })
            if u.status_code not in (200, 201, 206):
                raise RuntimeError(f"TikTok upload falló: {u.status_code} {u.text[:200]}")

    for _ in range(30):
        s = requests.post(f"{API}/post/publish/status/fetch/", headers=h, timeout=30,
                          json={"publish_id": publish_id}).json()
        status = s.get("data", {}).get("status")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            return f"TikTok {status} ({publish_id})"
        if status == "FAILED":
            raise RuntimeError(f"TikTok rechazó el vídeo: {s}")
        time.sleep(10)
    return f"TikTok en proceso ({publish_id})"
