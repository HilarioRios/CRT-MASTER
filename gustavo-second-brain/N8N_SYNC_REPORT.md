# N8N_SYNC_REPORT

Generado 2026-10-02. Integración n8n + FastAPI bridge + Drive, ejecutada end-to-end (no solo
código escrito — ver sección "Ejecución real" abajo).

```
N8N_RUNNING: TRUE
ORCHESTRATOR_RUNNING: TRUE
TOTAL_SOURCES: 345
READY_TO_SYNC: 0
SYNCED_BEFORE: 315
SYNCED_NOW: 0
SKIPPED: 0
FAILED: 0
MEMBERS_ONLY_PENDING: 30
OTHER_PENDING: 0
```

**URL local de n8n**: http://localhost:5678

## Por qué READY_TO_SYNC / SYNCED_NOW = 0

No es un fallo: el `run_pipeline.py` original ya hace fetch→normalize→chunk→**sync a Drive** en
una sola pasada continua por fuente (ver su docstring). Para el momento en que arrancó esta
integración, las 315 fuentes procesables ya habían llegado a `DRIVE_SYNCED` durante esa corrida —
no quedó ninguna en un estado intermedio (`PROCESSED`/`CHUNKED`/`INDEXED`) esperando subida. El
smoke test y el job de sync-ready corrieron igual, contra datos reales, y confirmaron el camino
de idempotencia (`already_synced`) en vez del de subida nueva — que es exactamente lo que hace
falta probar para que el workflow sea seguro de correr repetidamente (sección 9 de tu pedido).

## 1. Auditoría previa (antes de construir nada)

- `scripts/sync_drive.py`: ya resuelve subida idempotente, inmutabilidad de RAW, verificación de
  integridad por md5Checksum, reintentos con backoff. **No se reimplementó nada de esto** — el
  orchestrator lo importa y llama directo.
- `config/drive_structure.json`: la estructura de carpetas pedida (00_ADMIN...99_SYSTEM_LOGS,
  01_YOUTUBE/MentoTradingClub+Gustavom.Trader/00_INDEX+01_RAW+02_PROCESSED+03_METADATA) **ya
  existía completa**, creada en una fase anterior del proyecto. Verificado contra Drive real
  (no solo el JSON) con `get_file_metadata` sobre 2 file_id reales — coincide.
- `n8n/`: ya tenía `docker-compose.yml` corriendo (contenedor `gustavo-n8n-local`, puerto
  127.0.0.1:5678, instalado en una tarea anterior de esta misma sesión) y un primer workflow
  borrador (`orchestrate_pipeline.json`, inactivo). No se recreó el contenedor, se reutilizó.
- SQLite: `sources.processing_status`, `drive_sync` (file_id por rol), `errors` — todo reusado
  tal cual.

## 2. FastAPI bridge (`services/orchestrator_api.py`)

Corre con el `.venv` del proyecto, **no dentro del contenedor de n8n** (evita duplicar
ffmpeg/yt-dlp/faster-whisper ahí):

```
.venv/bin/uvicorn services.orchestrator_api:app --host 0.0.0.0 --port 8731
```

n8n (Docker, macOS) le pega vía `http://host.docker.internal:8731` — confirmado reachable desde
dentro del contenedor (`docker exec gustavo-n8n-local ... curl http://host.docker.internal:8731/health`
respondió 200 antes de tocar nada del workflow).

No reimplementa discovery/transcripts/normalization/chunking/index — solo decide qué fuentes
están "listas" (`processing_status IN ('PROCESSED','CHUNKED','INDEXED')`, es decir: procesadas
localmente pero no sincronizadas) y llama `sync_source()` tal cual.

Endpoints implementados: `GET /health`, `GET /status`, `POST /jobs/sync-ready`,
`POST /jobs/retry-drive-failed`, `GET /jobs/{job_id}`. Jobs en memoria (hilo en background por
job) — el bridge es efímero a propósito: si se reinicia a mitad de un job no se pierde ni
duplica nada en Drive/SQLite (idempotente), solo hay que volver a pedir el job.

**Nota operativa**: este proceso NO está en el `docker-compose.yml` (corre en el host, en el
venv). Si reiniciás la Mac o cerrás la terminal, hay que volver a levantarlo con el comando de
arriba antes de que el workflow de n8n pueda llamarlo. Es candidato a un `launchd`/servicio si
lo querés persistente — no lo configuré porque no estaba pedido explícitamente.

## 3. Workflow n8n: "Gustavo Second Brain — Sync Ready Sources"

`n8n/workflows/sync_second_brain.json`. Importado **inactivo** (confirmado:
`n8n export:workflow` → `"active": false`). Flujo exacto al pedido: Manual Trigger → GET /health
→ IF ok → POST /jobs/sync-ready → Wait (3s) → GET /jobs/{job_id} → IF sigue QUEUED/RUNNING
(vuelve a Wait, loop) → IF FAILED (Log error) / si no (Log summary).

Ningún nodo tiene secretos: son HTTP requests a `host.docker.internal`, sin autenticación (el
bridge corre solo en loopback del host, no expuesto). Nada de API keys/tokens/client secrets
impreso en consola ni en el JSON exportado — verificado.

Schedule Trigger: **no se activó**, tal como pediste.

## 4. Smoke test (3 fuentes)

Como ya no había fuentes "ready" (todo ya estaba sincronizado), el smoke test se hizo contra 3
fuentes `DRIVE_SYNCED` reales elegidas al azar, llamando la MISMA `sync_source()`:

| source_id | raw | processed | metadata |
|---|---|---|---|
| YT_CANAL_02_YnPAyVB5_KE | already_synced | already_synced | already_synced |
| YT_CANAL_02_9-J_jWzMRls | already_synced | already_synced | already_synced |
| YT_CANAL_02_JYHxxWO8RS4 | already_synced | already_synced | already_synced |

Verificación física en Drive (no solo SQLite) sobre uno de los `file_id`:
`YnPAyVB5_KE_transcript_raw.vtt`, `parentId` = carpeta `01_RAW` de `canal_02` en
`drive_structure.json` — coincide exactamente, archivo real, no trashed.

## 5. Ejecución real (no solo código)

- Orchestrator levantado y probado con `curl` contra los 5 endpoints — todos responden
  correctamente, incluido un 404 real para un `job_id` inexistente.
- `POST /jobs/sync-ready` corrido 2 veces seguidas contra el MASTER_INDEX en Drive: primera vez
  `action: created`, segunda vez `action: updated` **mismo file_id** — confirma que no duplica el
  archivo (sección 9 de tu pedido).
- El workflow de n8n se ejecutó de punta a punta vía `n8n execute --id=...` (un contenedor
  efímero `docker run --rm` compartiendo el mismo volumen `gustavo_n8n_data`, porque el proceso
  normal del contenedor ya ocupa el puerto interno del task broker — así evité tocar o reiniciar
  el contenedor que ya estaba corriendo). Resultado real, capturado: `IF health OK` → true,
  `POST /jobs/sync-ready` → `job_id` real, `GET /jobs/{job_id}` → `status: COMPLETED`, nodo final
  `Log summary` con el resumen formateado correctamente.
- `database/MASTER_INDEX.csv` regenerado con las columnas nuevas pedidas
  (`internal_classification`, `drive_raw_url`, `drive_processed_url`, `drive_metadata_url`,
  `last_synced`) y espejado a `00_ADMIN/MASTER_INDEX.csv` en Drive (confirmado con
  `get_file_metadata`, `parentId` correcto).
- `tests/test_build_master_index.py` (6/6) y `tests/test_run_pipeline.py` (18/18) siguen
  pasando después de los cambios en `scripts/build_master_index.py` y `scripts/run_pipeline.py`.

## 6. Los 30 members-only

`processing_status = 'PENDING_ACCESS'`, `internal_classification = 'YOUTUBE_MEMBERS_ONLY_EXCLUSIVE'`.
No se les inventó transcript ni se marcaron `DRIVE_SYNCED`. `run_pipeline.py` quedó parchado para
excluir `PENDING_ACCESS` de la selección normal Y del retry pass (mismo tipo de bug que ya habían
encontrado con `FAILED` antes de tener `select_all_failed()` — evité repetirlo). Cuando se
resuelva el acceso, el mismo pipeline los puede retomar sin cambiar nada de arquitectura: solo
hace falta volver a poner `processing_status='METADATA_READY'` (o el estado que corresponda) para
que `select_pending_batch()` los vuelva a tomar.

## 7. Video del bug (YT_CANAL_01_cSOcOpJvMS8)

Terminó correctamente ANTES de este reporte (ver `FULL_IMPORT_REPORT.md`, sección 2) — `av==18.1.0`
resolvió el bug, quedó `DRIVE_SYNCED` vía Whisper local, 6 chunks. Incluido normalmente en los 315.

## 8. Google Sheet del Master Index (punto 5, "si lo permite de forma robusta")

**No lo generé.** La integración de Drive disponible puede crear un Sheet nuevo o actualizar el
*nombre/carpeta* de un archivo existente, pero no reemplazar el *contenido* de un Google Sheet ya
creado — solo `sync_drive.py`/el orchestrator (vía la API directa de Drive, con
`MediaFileUpload`) pueden reemplazar contenido de un archivo, y eso es lo que mantiene
`00_ADMIN/MASTER_INDEX.csv` como CSV. Crear un Sheet nuevo en cada corrida violaría la regla de
no duplicar archivos (sección 9). Si querés el Sheet igual, puedo crear uno ahora como snapshot
puntual (no auto-actualizado) — decime.

## 9. Extensión: flujo completo "video nuevo → procesado" (pedido posterior)

A pedido explícito, se agregó el resto del diagrama (detección de video nuevo → pipeline →
Drive → índice), que hasta este punto no existía (`Sync Ready Sources` solo sincronizaba a
Drive lo que el pipeline YA había procesado local, no detectaba nada nuevo).

**Nuevos endpoints en el orchestrator:**
- `POST /jobs/detect-new`: corre, en este orden (el mismo orden de las fases originales del
  proyecto), `discover_videos_api.run()` → `discover_shorts_live_tabs.run()` →
  `classify_videos.run()`. Cero lógica duplicada. Los Shorts quedan excluidos en este mismo paso
  (antes de que el pipeline los vea), igual que los 762 videos ya existentes.
- `POST /jobs/run-pipeline`: corre `run_pipeline.run_import()` completo (el mismo que se usó
  para las 345 fuentes), tal cual.

**Nuevo workflow**: `n8n/workflows/detect_and_process.json` — "Gustavo Second Brain — Detect &
Process New Videos". Manual Trigger → health → detect-new (polling) → si falló: log error; si no
encontró nada nuevo listo: log "nada nuevo"; si encontró algo: run-pipeline (polling) → log
resumen o error. Importado **inactivo**.

**Ejecución real**: corrida de punta a punta vía `n8n execute` (mismo mecanismo de contenedor
efímero que la vez anterior). La cuota de la YouTube Data API sigue agotada ahora mismo (reinicia
~04:00 hora local, medianoche Pacífico) — así que `detect-new` falló como se esperaba, PERO esto
validó de verdad el camino completo de manejo de error: polling → detección de `FAILED` →
`Log detect error` con el mensaje real y saneado. El camino de éxito (nuevo video encontrado →
dispara run-pipeline) quedó validado por revisión de código y por el patrón ya probado en
`Sync Ready Sources`, pero no por una ejecución en vivo — no había forma de probarlo sin cuota.
Te recomiendo correrlo de nuevo después de las 04:00 para la validación en vivo.

## Seguridad

**Incidente real durante esta tarea, corregido en el momento**: al fallar `detect-new` por cuota
agotada, el `HttpError` de `googleapiclient` incluyó la URL completa del request, que para
llamadas con API key (no OAuth) trae `?key=<API_KEY_EN_TEXTO_PLANO>` — y eso llegó sin filtrar a
la respuesta de `GET /jobs/{job_id}` y a esta conversación (lo viste en mi mensaje de ese
momento). Verificado: **no quedó persistido en ningún archivo ni en SQLite** (busqué el patrón
`AIzaSy`/`key=` en todo el repo, en la tabla `errors`, y en `/tmp` — cero coincidencias). Arreglé
`services/orchestrator_api.py` con una función `_sanitize()` que redacta `key=`, `access_token=`
y headers `Bearer` antes de guardar o devolver cualquier mensaje de error, aplicada en los 7
puntos donde se guardaba `str(exc)`. Reprobado: el mismo error ahora devuelve `key=***REDACTED***`.

**Recomendación**: aunque no quedó en ningún archivo, la key SÍ apareció en texto plano en esta
conversación en un momento dado. Por las dudas, te sugiero rotarla en Google Cloud Console
(Credenciales → la API key de `YOUTUBE_API_KEY`) — no es una emergencia (es una API key de solo
lectura sobre datos públicos de YouTube, no un token con acceso a cuentas), pero es la práctica
correcta.

Fuera de ese incidente (ya corregido): no se imprimió ningún OAuth token, refresh token ni client
secret en ningún momento. No se commiteó nada — no se corrió ningún `git add`/`git commit` en
esta tarea.
