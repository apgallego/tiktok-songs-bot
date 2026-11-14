# Contexto del proyecto (para Claude Code)

Proyecto creado en un chat de claude.ai. El usuario habla español.

## Objetivo
Automatismo que, una vez al día y sin intervención, lee una canción y su artista de `songs.csv`,
genera un guion corto sobre la canción y el artista, crea un vídeo animado vertical de 20-30 s y lo
publica en TikTok, Instagram Reels y YouTube Shorts.

## Requisito clave
**Coste cero**, tanto al montarlo como al mantenerlo. No proponer servicios de pago
(Creatomate, ElevenLabs de pago, Ayrshare, Upload-Post, etc.). El usuario quiere "montarlo y olvidarse".

## Decisiones tomadas
- Ejecución: GitHub Actions (cron diario, repositorio público) con Python, no n8n.
- Guion: API gratuita de Gemini (`GEMINI_MODEL`, por defecto gemini-2.5-flash), salida JSON.
- Voz: edge-tts (por defecto es-ES-AlvaroNeural) con tiempos por palabra para los subtítulos.
- Imágenes: Pollinations.ai; si falla, fondo degradado con Pillow.
- Montaje: FFmpeg (zoompan + xfade + subtítulos ASS palabra a palabra + título + música de `music/`).
- YouTube: Data API v3 con refresh token (los vídeos son privados hasta la auditoría de Google).
- Instagram: API de Instagram con login de Instagram; el vídeo se aloja en una release de GitHub.
- TikTok: Content Posting API, modo `inbox` (borrador) hasta que aprueben la app; luego `TIKTOK_MODE=direct`.
- Los tokens renovados se guardan como secretos con `gh secret set` usando `GH_PAT`.
- Sin canción original, sin citar letras, sin caras reales de artistas (derechos de autor).

## Estado
- Probado en local: el render del vídeo y el flujo de `main.py` con llamadas de red simuladas.
- NO probado contra las APIs reales (Gemini, edge-tts, Pollinations, YouTube, Instagram, TikTok).
- Siguiente paso: subir a GitHub, configurar `GEMINI_API_KEY`, lanzar con dry_run=1 y corregir errores.
  La guía completa de puesta en marcha está en README.md.
