"""Proceso diario: lee la siguiente canción de songs.csv, crea el vídeo y lo publica."""
import csv
import datetime as dt
import glob
import os
import random
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))

import images  # noqa: E402
import music as music_lib  # noqa: E402
import resources  # noqa: E402
import script_gen  # noqa: E402
import tts  # noqa: E402
import upload_instagram  # noqa: E402
import upload_tiktok  # noqa: E402
import upload_youtube  # noqa: E402
import video  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONGS = os.path.join(ROOT, "songs.csv")
HISTORY = os.path.join(ROOT, "historial.csv")
OUT = os.path.join(ROOT, "output")


def next_song():
    with open(SONGS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows):
        if not (row.get("publicado") or "").strip():
            return rows, i
    return rows, None


def mark_done(rows, idx):
    rows[idx]["publicado"] = dt.date.today().isoformat()
    with open(SONGS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cancion", "artista", "publicado"])
        w.writeheader()
        w.writerows(rows)


def log_history(song, artist, results):
    new = not os.path.exists(HISTORY)
    with open(HISTORY, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fecha", "cancion", "artista", "resultado"])
        w.writerow([dt.datetime.now().isoformat(timespec="minutes"), song, artist, " | ".join(results)])


def main() -> int:
    rows, idx = next_song()
    if idx is None:
        print("No quedan canciones pendientes en songs.csv. Añade más filas.")
        return 1
    song, artist = rows[idx]["cancion"].strip(), rows[idx]["artista"].strip()
    print(f"▶ Canción de hoy: {song} — {artist}")
    os.makedirs(OUT, exist_ok=True)

    print("0/4 Buscando recursos (portada y datos de Wikipedia)…")
    cover_src = resources.fetch_cover(song, artist, os.path.join(OUT, "cover_src.jpg"))
    try:
        context = resources.wiki_context(song, artist)
    except Exception as e:
        print(f"  Wikipedia falló: {e}")
        context = ""
    print(f"    Portada: {'sí' if cover_src else 'no'} · Datos Wikipedia: {'sí' if context else 'no'}")

    print("1/4 Generando guion con Gemini…")
    s = script_gen.generate_script(song, artist, context)
    print("   ", s["narracion"])

    print("2/4 Generando voz…")
    voice = os.path.join(OUT, "voice.mp3")
    words, dur = tts.synthesize(s["narracion"], voice)
    print(f"    {dur:.1f} s de audio")

    print("3/4 Generando imágenes…")
    seed = random.randint(1, 10**6)
    imgs = []
    if cover_src:
        imgs.append(images.cover_card(cover_src, os.path.join(OUT, "img_cover.jpg")))
    for i, prompt in enumerate(s["imagenes"][: 5 - len(imgs)]):
        p = os.path.join(OUT, f"img{i}.jpg")
        images.fetch_image(prompt, p, seed + i)
        imgs.append(p)

    print("4/4 Montando vídeo…")
    # prioridad: tus mp3 en music/ (si los hay); si no, una pista libre de Wikimedia Commons
    tracks = glob.glob(os.path.join(ROOT, "music", "*.mp3"))
    music, credit = None, ""
    if tracks:
        music = random.choice(tracks)
    else:
        bg = music_lib.fetch_background(OUT)
        if bg:
            music = bg["path"]
            credit = f"Música: {bg['title']} de {bg['artist']} ({bg['license']}), Wikimedia Commons"
            print(f"    {credit}")
    out_video = os.path.join(OUT, "video.mp4")
    video.render(imgs, voice, words, dur, s["titulo"], out_video, OUT, music)
    print(f"    Vídeo listo: {out_video}")

    tags = s["hashtags"][:8]
    caption = f"{s['descripcion']}\n\n{' '.join(tags)}"
    title = f"{song} - {artist}: {s['titulo']}" if s["titulo"] not in song else f"{song} - {artist}"
    if credit:
        caption += f"\n\n{credit}"

    if os.getenv("DRY_RUN") == "1":
        print("DRY_RUN activo: no se publica ni se marca la canción.")
        log_history(song, artist, [f"DRY_RUN | {credit or 'música local o ninguna'}"])
        return 0

    results, failures, attempted = [], 0, 0
    tag = f"video-{dt.date.today().isoformat()}"
    platforms = [
        ("YouTube", upload_youtube.enabled, lambda: upload_youtube.upload(
            out_video, title, f"{s['descripcion']}\n\n{s['narracion']}\n\n{' '.join(tags)}", tags)),
        ("Instagram", upload_instagram.enabled, lambda: upload_instagram.upload(out_video, caption, tag)),
        ("TikTok", upload_tiktok.enabled, lambda: upload_tiktok.upload(out_video, caption)),
    ]
    for name, is_on, do in platforms:
        if not is_on():
            print(f"  {name}: sin configurar, se omite")
            continue
        attempted += 1
        try:
            res = do()
            print(f"  ✔ {name}: {res}")
            results.append(f"{name} OK {res}")
        except Exception as e:
            failures += 1
            traceback.print_exc()
            print(f"  ✘ {name}: {e}")
            results.append(f"{name} ERROR {str(e)[:150]}")

    if attempted == 0:
        print("Ninguna red social configurada todavía: el vídeo queda como prueba "
              "(descárgalo en Actions > Artifacts) y la canción sigue pendiente.")
        return 0

    if failures == attempted:
        log_history(song, artist, results)
        print("Todas las subidas fallaron; la canción queda pendiente para mañana.")
        return 1

    mark_done(rows, idx)
    log_history(song, artist, results or ["sin plataformas configuradas"])
    # si alguna falló, terminamos con error para que GitHub te avise por email
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
