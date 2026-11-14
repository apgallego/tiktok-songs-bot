"""Ejecútalo UNA vez en tu PC para obtener el TIKTOK_REFRESH_TOKEN.

  pip install requests
  python tools/tiktok_token.py CLIENT_KEY CLIENT_SECRET REDIRECT_URI

REDIRECT_URI debe ser exactamente la que registraste en tu app de TikTok
(por ejemplo, la URL de tu repositorio: https://github.com/tu-usuario/canciones-bot).
"""
import secrets
import sys
import urllib.parse

import requests

key, secret, redirect = sys.argv[1], sys.argv[2], sys.argv[3]
state = secrets.token_urlsafe(8)
url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": key,
    # añade ",video.publish" cuando TikTok te apruebe la publicación directa
    "scope": sys.argv[4] if len(sys.argv) > 4 else "user.info.basic,video.upload",
    "response_type": "code",
    "redirect_uri": redirect,
    "state": state,
})
print("1) Abre esta URL, entra con tu cuenta de TikTok y autoriza:\n")
print(url)
print("\n2) Te redirigirá a tu REDIRECT_URI. Copia la URL COMPLETA de la barra del navegador")
back = input("   y pégala aquí: ").strip()
code = urllib.parse.parse_qs(urllib.parse.urlparse(back).query)["code"][0]

r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
    "client_key": key, "client_secret": secret, "code": code,
    "grant_type": "authorization_code", "redirect_uri": redirect,
}, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
data = r.json()
if "refresh_token" not in data:
    sys.exit(f"Error: {data}")
print("\nGuarda estos secretos en GitHub:\n")
print("TIKTOK_CLIENT_KEY    =", key)
print("TIKTOK_CLIENT_SECRET =", secret)
print("TIKTOK_REFRESH_TOKEN =", data["refresh_token"])
