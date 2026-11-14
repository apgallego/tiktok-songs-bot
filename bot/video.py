"""Monta el vídeo vertical 1080x1920 con FFmpeg: zoom animado sobre las imágenes,
transiciones, subtítulos palabra a palabra, título y música de fondo."""
import os
import random
import re
import subprocess

W, H, FPS = 1080, 1920, 30
XFADE = 0.5  # duración de cada transición (s)
TRANSITIONS = ["fade", "slideleft", "circleopen", "smoothup", "wipeleft", "radial"]
FONT = os.getenv("VIDEO_FONT", "DejaVu Sans")


# ---------- subtítulos (formato ASS) ----------

def _ts(t: float) -> str:
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def _chunks(words: list, max_words: int = 3) -> list:
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,;:!?…]$", w["text"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words: list, title: str, total: float, offset: float, path: str) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{FONT},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,560,1
Style: Title,{FONT},58,&H00FFFFFF,&H00FFFFFF,&H00202020,&H00000000,-1,0,0,0,100,100,1,0,3,18,0,8,80,80,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [
        f"Dialogue: 1,{_ts(0)},{_ts(total)},Title,,0,0,0,,"
        f"{{\\fad(300,0)}}{_esc(title.upper())}"
    ]
    chunks = _chunks(words)
    for ci, chunk in enumerate(chunks):
        next_start = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else chunk[-1]["end"] + 0.6
        for wi, w in enumerate(chunk):
            start = w["start"] + offset
            end = (chunk[wi + 1]["start"] if wi + 1 < len(chunk) else next_start) + offset
            parts = []
            for wj, w2 in enumerate(chunk):
                txt = _esc(w2["text"].upper())
                # palabra que se está diciendo en amarillo
                parts.append("{\\c&H00E5FF&}" + txt + "{\\c&HFFFFFF&}" if wj == wi else txt)
            pop = "{\\fscx85\\fscy85\\t(0,110,\\fscx100\\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{pop}{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")


# ---------- render ----------

def render(images: list, voice: str, words: list, voice_dur: float, title: str,
           out_path: str, workdir: str, music: str | None = None) -> None:
    lead_in, tail = 0.3, 1.2
    total = voice_dur + lead_in + tail
    n = len(images)
    clip = (total + (n - 1) * XFADE) / n
    frames = int(round(clip * FPS))

    build_ass(words, title, total, lead_in, os.path.join(workdir, "subs.ass"))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for img in images:
        cmd += ["-i", os.path.abspath(img)]
    cmd += ["-i", os.path.abspath(voice)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", os.path.abspath(music)]

    rnd = random.Random(title)
    f = []
    for i in range(n):
        zin = f"1+0.13*on/{frames}"
        zout = f"1.13-0.13*on/{frames}"
        z = zin if i % 2 == 0 else zout
        # ligero desplazamiento horizontal alternado
        x = "iw/2-(iw/zoom/2)" + (f"+{rnd.choice([-1, 1])}*on*0.6" if i % 3 == 2 else "")
        f.append(
            f"[{i}:v]scale={W * 2}:{H * 2},setsar=1,"
            f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p[v{i}]"
        )
    prev = "v0"
    for i in range(1, n):
        offset = i * (clip - XFADE)
        tr = TRANSITIONS[(i - 1) % len(TRANSITIONS)]
        f.append(f"[{prev}][v{i}]xfade=transition={tr}:duration={XFADE}:offset={offset:.3f}[x{i}]")
        prev = f"x{i}"
    f.append(
        f"[{prev}]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.28:t=fill,"
        f"subtitles=subs.ass,trim=duration={total:.3f},format=yuv420p[vout]"
    )
    ms = int(lead_in * 1000)
    f.append(f"[{n}:a]adelay={ms}|{ms},apad,atrim=duration={total:.3f}[voice]")
    if music:
        f.append(
            f"[{n + 1}:a]volume=0.13,atrim=duration={total:.3f},"
            f"afade=t=in:d=0.8,afade=t=out:st={total - 1.5:.3f}:d=1.5[bg]"
        )
        f.append("[voice][bg]amix=inputs=2:duration=first:normalize=0,"
                 "loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    else:
        f.append("[voice]loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

    cmd += [
        "-filter_complex", ";".join(f),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart", "-t", f"{total:.3f}",
        os.path.abspath(out_path),
    ]
    subprocess.run(cmd, check=True, cwd=workdir)
