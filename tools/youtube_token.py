"""Ejecútalo UNA vez en tu PC para obtener el YT_REFRESH_TOKEN.

  pip install google-auth-oauthlib
  python tools/youtube_token.py ruta/al/client_secret.json

Se abrirá el navegador: entra con la cuenta del canal y acepta.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(
    path, scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
info = json.load(open(path))
info = info.get("installed") or info.get("web")
print("\nCopia estos tres valores como secretos en GitHub:\n")
print("YT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
