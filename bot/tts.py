"""Voz en off gratuita con edge-tts (voces neuronales de Microsoft Edge)."""
import asyncio
import os
import subprocess

import edge_tts

VOICE = os.getenv("TTS_VOICE", "es-ES-AlvaroNeural")  # o es-ES-ElviraNeural
RATE = os.getenv("TTS_RATE", "+8%")


async def _synth(text: str, out_mp3: str) -> list:
    try:
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:  # versiones antiguas de edge-tts
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    words = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append(
                    {"text": chunk["text"], "start": start,
                     "end": start + chunk["duration"] / 1e7}
                )
    return words


def audio_duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path]
    )
    return float(out.strip())


def estimate_word_timings(text: str, duration: float) -> list:
    """Si la voz no da tiempos por palabra, los repartimos según la longitud."""
    tokens = text.split()
    total = sum(len(t) + 2 for t in tokens)
    t, words = 0.15, []
    usable = max(duration - 0.3, 1)
    for tok in tokens:
        d = usable * (len(tok) + 2) / total
        words.append({"text": tok, "start": t, "end": t + d})
        t += d
    return words


def synthesize(text: str, out_mp3: str) -> tuple[list, float]:
    words = []
    for attempt in range(3):
        try:
            words = asyncio.run(_synth(text, out_mp3))
            break
        except Exception:
            if attempt == 2:
                raise
    duration = audio_duration(out_mp3)
    # edge-tts da las palabras sin la puntuación; recuperamos el texto original
    tokens = text.split()
    if len(words) < len(tokens) * 0.6:
        words = estimate_word_timings(text, duration)
    elif len(words) == len(tokens):
        for w, tok in zip(words, tokens):
            w["text"] = tok
    return words, duration
