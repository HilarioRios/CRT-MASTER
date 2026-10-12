# Gustavo Second Brain

Base de conocimiento verificable, trazable y consultable del contenido de Gustavo (YouTube primero, luego el resto del ecosistema). Toda respuesta debe venir acompañada de fuente, video y timestamp — nunca se inventa una atribución sin evidencia.

Ver `SETUP_STATUS.md` para el estado del entorno y lo que falta para poder avanzar.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar YOUTUBE_API_KEY y los dos canales
python scripts/db.py   # inicializa database/gustavo_brain.sqlite
```

## Flujo

1. `scripts/discover_videos.py` — descubre todos los videos de los dos canales (solo metadata, no descarga nada). Genera `DISCOVERY_REPORT.md`.
2. Piloto de 10 videos (5 por canal) corre el pipeline completo: transcripción -> normalización -> chunking -> índice -> sync a Drive. Genera `PILOT_REPORT.md`.
3. Quality gate: preguntas de prueba contra el buscador. Si no hay evidencia suficiente, se corrige antes de escalar.
4. Solo tras tu confirmación explícita ("LANZAR IMPORTACIÓN COMPLETA") se procesa el catálogo completo (300+ videos), de forma idempotente y reanudable.

## Cómo reanudar / reintentar

El estado de cada video vive en `database/gustavo_brain.sqlite` (tabla `sources.processing_status`). Si el proceso se interrumpe, `run_pipeline.py` retoma desde el último estado persistido en vez de reprocesar desde cero. Los errores quedan en la tabla `errors` y se pueden reintentar con `retry_failed` (no procesa dos veces el mismo `video_id` innecesariamente).

## Buscar

```bash
python scripts/query.py "¿Cómo define Gustavo el bias diario?"
```

Devuelve título, canal, timestamp, fragmento y deep link a YouTube. Nunca inventa una respuesta sin evidencia — si no encuentra nada, lo dice explícitamente.

## Costos

Zero-cost mode: todo corre local (SQLite, yt-dlp, faster-whisper, embeddings locales, n8n self-hosted). Ninguna API paga se usa sin autorización explícita previa.

## Privacidad

Cada fuente se clasifica como `PUBLIC`, `PRIVATE_INTERNAL` o `SENSITIVE_INTERNAL` (ver `config/taxonomy.yaml`). El contenido de YouTube es público; llamadas de ventas, onboarding y datos de clientes nunca se tratan como público.

## Credenciales OAuth

Dos credenciales OAuth **completamente separadas**, cada una con su propio cliente y su propio token -- ninguna se reutiliza entre sí:

- **YouTube** (`credentials/youtube_oauth_web.json`, tipo "Web application"): autoriza las cuentas de Gustavo para leer captions oficiales. Dos tokens, uno por canal: `tokens/youtube_gustavo.json` (MentoTrading) y `tokens/youtube_gustavo_trader.json` (Gustavom.Trader). Se obtienen con `scripts/authorize_youtube_remote.py` (ver su docstring).
- **Drive** (`credentials/google_drive_oauth_client.json`, tipo "Desktop app", scope `drive` completo -- ver el porqué en `scripts/authorize_drive.py`): autoriza la sincronización con el Drive del Segundo Cerebro. Token en `tokens/google_drive_hilario.json`. Se obtiene con:
  ```bash
  .venv/bin/python scripts/authorize_drive.py
  ```
  Requiere crear antes, en Google Cloud Console (mismo proyecto que el cliente de YouTube), un OAuth Client tipo **Desktop app** con la **Google Drive API** habilitada, y guardar el JSON descargado como `credentials/google_drive_oauth_client.json`.

Ningún script de Drive lee, modifica ni sobreescribe los tokens de YouTube, y viceversa.

## Drive

- Fuente original de Gustavo (NO se modifica, solo se lee): carpeta `GOOGLE_DRIVE_SOURCE_FOLDER_ID` en `.env`.
- Destino del Segundo Cerebro: carpeta `GOOGLE_DRIVE_SECOND_BRAIN_FOLDER_ID` en `.env`. Estructura de subcarpetas ya creada, IDs en `config/drive_structure.json`.
- Sincronización: `scripts/sync_drive.py` (idempotente, RAW inmutable, reintentos, verificación de integridad por checksum, resumible -- ver su docstring).

## n8n

Self-hosted vía Docker (`docker compose up -d` desde la raíz), solo una vez validado el pipeline. Ver `n8n/README.md`.
