# SETUP_STATUS

Generado: 2026-10-01. Auditoría del entorno antes de tocar cualquier video.

## Dependencias de sistema

| Dependencia | Estado | Detalle |
|---|---|---|
| macOS / arquitectura | AVAILABLE | macOS 26.6.2, arm64 (Apple Silicon) — sin GPU NVIDIA, Whisper corre en CPU |
| Python | AVAILABLE | 3.14.7 (Homebrew, `/opt/homebrew/bin/python3`) — `externally-managed-environment`, se usa venv del proyecto (`.venv/`, ya creado) |
| Git | AVAILABLE | 2.50.1 |
| Docker | AVAILABLE | 29.4.3 |
| Docker Compose | AVAILABLE | v5.1.3 (plugin `docker compose`) |
| FFmpeg | AVAILABLE | 8.1.1 |
| yt-dlp | AVAILABLE | 2026.03.17 |
| sqlite3 (CLI) | AVAILABLE | 3.51.0 |
| Node.js | AVAILABLE | v22.22.2 (no es requisito del pipeline Python, pero ya está si se necesita para n8n) |
| faster-whisper | MISSING | No instalado a nivel sistema. Se instala dentro del venv vía `requirements.txt` cuando se corra el piloto (FASE 4-5), no hace falta ahora |
| sentence-transformers | MISSING (igual, vía requirements.txt cuando se construya el índice semántico, FASE 17) |

Ninguna herramienta de pago fue instalada ni se planea instalar sin autorización explícita (zero-cost mode).

## Skills / tools ya disponibles en este entorno

| Área | Estado | Detalle |
|---|---|---|
| Google Drive | AVAILABLE (lectura + escritura condicionada) | Conector MCP `mcp__claude_ai_Google_Drive__*` ya autenticado y funcionando — ver sección Drive abajo para permisos específicos por carpeta |
| YouTube (Data API) | NEEDS_AUTH | No hay skill/conector de YouTube instalado. Se implementa en Python contra YouTube Data API v3 con una simple API key (no requiere OAuth para datos públicos: metadata, uploads playlist, etc.) |
| YouTube captions oficiales (OAuth) | NOT AVAILABLE EN ESTA SESIÓN | Esta sesión es no-interactiva (headless) — no puede completar un flujo OAuth de la cuenta de Gustavo aunque quisiéramos. Cascada de transcripción arranca directo en yt-dlp (método 2/3) y cae a Whisper local (método 4) |
| browser / APIs genéricas | AVAILABLE | Playwright/chrome-devtools MCP disponibles si hiciera falta scraping, pero no se necesita: todo se resuelve con la API pública + yt-dlp |
| filesystem | AVAILABLE | Bash/Read/Write/Edit nativos |
| Google Docs / Sheets | AVAILABLE (mismo conector Drive) | Se puede usar para el MASTER INDEX en `00_ADMIN` si el usuario lo pide, pero el CSV local en `database/` es la fuente de verdad primaria |
| Skill de transcripción dedicada | NO EXISTE | Se implementa directo en Python (yt-dlp + faster-whisper), no hace falta una skill extra |

No se instaló ninguna herramienta duplicada: todo lo que ya estaba disponible (Drive, filesystem, Docker) se reutiliza tal cual.

## Google Drive — hallazgos (lectura no destructiva)

**Carpeta origen** (`1kggFa7toDnOvD3WCJf2tI_iaNDEwehr6`, "Cliente Gustavom.Trader", owner `growthia.us@gmail.com`):
- Accesible, permiso `writer` para la cuenta conectada (y para "anyone with link").
- **No se tocó ni se tocará**: regla dura del proyecto. Se usa solo como fuente de lectura.
- La búsqueda de contenido directo dentro de esta carpeta no devolvió archivos hijos (`parentId` query vacía) — y confirmé que el mecanismo de búsqueda por `parentId` funciona bien (lo probé contra otra carpeta y sí trajo resultados). La explicación más probable no es que la carpeta esté vacía: es que una carpeta compartida por "link" que la cuenta conectada (`sociodecontenido@gmail.com`) nunca "agregó a Mi unidad" a veces no expone sus hijos vía API para esa cuenta, aunque `get_file_metadata` sobre la carpeta sí funcione. Antes de asumir que está vacía, valdría la pena que abras esa carpeta una vez desde tu Drive con `sociodecontenido@gmail.com` (o la cuenta que corresponda) para que quede indexada.

**Carpeta destino** (`1OCPpwwGtRmIgAXfhFNmJ9WL9uBSP-OXU`, "Segundo cerebro", owner `jonathan.rios2703@gmail.com`):
- Accesible, pero la cuenta conectada **solo tiene permiso `reader`** (vía "anyone with link"). `canAddChildren: false`.
- **NEEDS_AUTH**: no puedo crear la estructura `00_ADMIN / 01_YOUTUBE / ... / 99_SYSTEM_LOGS` ahí hasta que se otorgue permiso de edición a la cuenta conectada, o se me indique otra carpeta destino sobre la que sí tenga permiso de escritura. No improvisé una carpeta alternativa — ver "NECESITO DE HILARIO" abajo.

No se encontraron, en una búsqueda razonable del Drive accesible, los dos canales de YouTube de Gustavo documentados con certeza (hay varias carpetas "Youtube" sueltas de otros clientes/proyectos, ninguna claramente ligada a Gustavo con URLs de canal). Por eso los pido explícitamente abajo en vez de adivinar.

## Estructura local creada (FASE 1)

```
gustavo-second-brain/
├── README.md, SETUP_STATUS.md, .env.example, .gitignore, requirements.txt, docker-compose.yml
├── config/ (channels.json, settings.yaml, taxonomy.yaml)
├── data/{raw,processed,chunks,metadata,state}/youtube/
├── database/ (schema.sql + gustavo_brain.sqlite ya inicializada y verificada)
├── scripts/ (db.py — probado con pytest, 2/2 OK)
├── tests/ (test_db.py)
├── logs/, n8n/ (docker-compose + README, inactivo)
└── .venv/ (entorno virtual del proyecto, pytest instalado)
```

Git inicializado en `gustavo-second-brain/` (repo propio, separado del resto de "Gustavo Tradinf").

## NECESITO DE HILARIO

1. **YOUTUBE_API_KEY** — Google Cloud Console → crear/usar un proyecto → habilitar "YouTube Data API v3" → Credenciales → API key (no hace falta OAuth para esto). Pegarla en `gustavo-second-brain/.env` como `YOUTUBE_API_KEY=...` (nunca la pegues en el chat).
2. **Los dos URLs (o @handle) de los canales de YouTube de Gustavo** — no los pude confirmar con certeza en el Drive accesible. Necesito `YOUTUBE_CHANNEL_1_URL` y `YOUTUBE_CHANNEL_2_URL`.
3. **Permiso de escritura en la carpeta destino del Segundo Cerebro** (`1OCPpwwGtRmIgAXfhFNmJ9WL9uBSP-OXU`) — ahora mismo la cuenta conectada (`sociodecontenido@gmail.com`) solo puede leerla (permiso `reader` vía "anyone with link"; el owner es `jonathan.rios2703@gmail.com`). Compartila con permiso de **Editor** directamente a `sociodecontenido@gmail.com`, o decime si preferís que usemos otra carpeta Drive donde esa cuenta ya tenga permiso de escritura.

En cuanto tenga esos tres datos sigo solo con FASE 2 (estructura en Drive) y FASE 3 (discovery de los videos) sin pedirte nada más hasta el checkpoint del piloto.
