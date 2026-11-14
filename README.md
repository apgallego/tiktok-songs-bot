# 🎵 Bot de vídeos sobre canciones (100 % gratis)

Cada día, solo, en la nube de GitHub:

1. Coge la siguiente canción pendiente de `songs.csv`.
2. Escribe un guion de unos 25 s con **Gemini** (API gratuita).
3. Genera la voz en off con **edge-tts** (gratis).
4. Crea 4 ilustraciones con **Pollinations.ai** (gratis).
5. Monta un vídeo vertical 1080x1920 con **FFmpeg**: zoom animado, transiciones, subtítulos palabra a palabra, título y música de fondo.
6. Lo sube a **YouTube Shorts**, **Instagram Reels** y **TikTok**.
7. Marca la canción como publicada y guarda un registro en `historial.csv`.

No necesitas tener el PC encendido. Coste: 0 €.

---

## Puesta en marcha (una sola vez, ~1 h)

Puedes ir activando las redes de una en una: si una red no tiene sus claves, el bot simplemente la salta.

### 1. Sube el proyecto a GitHub
1. Crea una cuenta en github.com (si no tienes).
2. **New repository** → nombre `canciones-bot` → **Public** (necesario para que las Actions sean ilimitadas y para que Instagram pueda descargar el vídeo; tus claves siguen siendo secretas).
3. **Add file → Upload files** y arrastra todo el contenido de esta carpeta (incluida la carpeta `.github`).
   > Si el navegador no sube la carpeta `.github` (empieza por punto), crea el fichero a mano: **Add file → Create new file**, nombre `.github/workflows/daily.yml` y pega su contenido.

Las claves se guardan en **Settings → Secrets and variables → Actions → New repository secret**.

### 2. Gemini (obligatorio)
1. Entra en https://aistudio.google.com → **Get API key** → crear.
2. Secreto: `GEMINI_API_KEY`.

### 3. Prueba sin publicar
**Actions → Vídeo diario → Run workflow** (deja `dry_run` en `1`). En 3-5 minutos tendrás el vídeo en la ejecución, apartado **Artifacts**. Si te gusta, sigue.

### 4. YouTube Shorts
1. https://console.cloud.google.com → crea un proyecto → **APIs y servicios → Biblioteca** → activa **YouTube Data API v3**.
2. **Pantalla de consentimiento OAuth** → tipo *Externo* → rellena lo mínimo → añade tu email como usuario de prueba → y después pulsa **Publicar aplicación** (estado *En producción*). ⚠️ Si la dejas en *Prueba*, el token caduca a los 7 días.
3. **Credenciales → Crear credenciales → ID de cliente OAuth → Aplicación de escritorio** → descarga el JSON.
4. En tu PC: `pip install google-auth-oauthlib` y `python tools/youtube_token.py client_secret.json`. Acepta el aviso de "app no verificada" (es la tuya).
5. Secretos: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

> Google publica en **privado** los vídeos subidos por API desde proyectos no auditados. La auditoría es gratuita: formulario "YouTube API Services - Audit and Quota Extension". Hasta entonces, los vídeos quedan en tu canal y puedes ponerlos públicos a mano.

### 5. Instagram Reels
1. Tu cuenta de Instagram tiene que ser **profesional** (Creador o Empresa; es gratis, se cambia en la app).
2. https://developers.facebook.com → **Crear app** → caso de uso *Administrar mensajes y contenido en Instagram*.
3. En **API de Instagram con inicio de sesión de Instagram** → añade tu cuenta → **Generar token**. Acepta los permisos (incluido `instagram_business_content_publish`).
4. Copia el token y averigua tu ID abriendo en el navegador:
   `https://graph.instagram.com/v22.0/me?fields=user_id,username&access_token=TU_TOKEN`
5. Secretos: `IG_ACCESS_TOKEN` y `IG_USER_ID` (el valor `user_id`).

### 6. TikTok
1. https://developers.tiktok.com → **Manage apps → Connect an app**.
2. Añade los productos **Login Kit** y **Content Posting API**. Como *Redirect URI* pon la URL de tu repo (p. ej. `https://github.com/tu-usuario/canciones-bot`).
3. Si la app está en *Sandbox*, añade tu cuenta de TikTok como usuario de prueba.
4. En tu PC: `python tools/tiktok_token.py CLIENT_KEY CLIENT_SECRET https://github.com/tu-usuario/canciones-bot` y sigue las instrucciones.
5. Secretos: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`.

> Hasta que TikTok revise tu app, el vídeo llega como **borrador a tu bandeja de TikTok** (te sale una notificación y lo publicas con un toque). Cuando te la aprueben (envía la app a revisión desde el panel, es gratis), crea la variable `TIKTOK_MODE` = `direct` en **Settings → Secrets and variables → Actions → Variables** y vuelve a sacar el token añadiendo `user.info.basic,video.upload,video.publish` como cuarto parámetro del script.

### 7. Que los tokens no caduquen nunca (`GH_PAT`)
Instagram y TikTok renuevan sus tokens; el bot guarda los nuevos solo si le das permiso:
1. GitHub → tu foto → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate**.
2. Repositorio: solo `canciones-bot`. Permiso: **Secrets → Read and write**. Caducidad: la más larga posible (GitHub te avisará por email antes de que caduque).
3. Secreto: `GH_PAT`.

### 8. Música de fondo (opcional)
Mete 3-10 mp3 instrumentales sin derechos (Pixabay Music, Biblioteca de audio de YouTube) en la carpeta `music/`. Nunca la canción original.

---

## Uso diario
- **Añadir canciones:** edita `songs.csv` desde la web de GitHub (lápiz ✏️). Una fila por vídeo: `cancion,artista,` (deja `publicado` vacío).
- **Hora:** se lanza a las 17:23 UTC (18:23 en España en invierno). Cámbiala en `.github/workflows/daily.yml` (línea `cron`).
- **Si algo falla:** GitHub te manda un email. La ejecución (pestaña **Actions**) muestra el motivo y el vídeo queda en **Artifacts**. Si fallan todas las redes, la canción se reintenta al día siguiente.
- **Voz:** variable `TTS_VOICE` (por defecto `es-ES-AlvaroNeural`; femenina: `es-ES-ElviraNeural`; latina: `es-MX-JorgeNeural`).

## Avisos
- **Datos:** la IA puede equivocarse con fechas o anécdotas. El guion le pide solo datos muy conocidos, pero revisa de vez en cuando lo publicado (`historial.csv` y la narración en el log).
- **Derechos:** el bot no usa la canción original, ni cita la letra, ni pinta caras reales de los artistas. Mantenlo así para evitar bloqueos.
- **Servicios gratuitos:** Pollinations y edge-tts no son oficiales y podrían cambiar. Si Pollinations falla, el vídeo sale con fondos degradados en lugar de ilustraciones; si cambia algo de las APIs, el email de error te avisará.
