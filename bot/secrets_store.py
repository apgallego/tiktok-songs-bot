"""Guarda tokens renovados como secretos del repositorio (necesita el secreto GH_PAT).
Así los tokens de Instagram y TikTok no caducan nunca y no tienes que tocar nada."""
import os
import subprocess


def save_secret(name: str, value: str) -> bool:
    pat = os.getenv("GH_PAT")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not pat or not repo or not value:
        print(f"  (no se guarda {name}: falta GH_PAT)")
        return False
    env = {**os.environ, "GH_TOKEN": pat}
    r = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo, "--body", value],
        env=env, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  No se pudo guardar {name}: {r.stderr.strip()}")
        return False
    print(f"  Secreto {name} actualizado")
    return True
