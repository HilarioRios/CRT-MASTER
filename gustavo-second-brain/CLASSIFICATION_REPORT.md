# CLASSIFICATION_REPORT

## DISCOVERY_RECONCILIATION

- **COUNT(DISTINCT video_id) real en SQLite: 762**

### Por canal
- Gustavom.Trader: 633
- MentoTrading: 129

### Integridad de datos
- Duplicados logicos (mismo video_id repetido): 0
- Sources sin fila en youtube_videos (huerfanos): 0
- Filas en youtube_videos sin source (huerfanos): 0

### Desglose por canal + availability + cuando se insertaron
| canal | availability | cantidad | primera insercion | ultima insercion |
|---|---|---|---|---|
| Gustavom.Trader | available | 362 | 2026-10-01 22:56:18 | 2026-10-01 22:56:19 |
| Gustavom.Trader | members_only | 30 | 2026-10-01 21:03:10 | 2026-10-01 21:05:28 |
| Gustavom.Trader | public | 241 | 2026-10-01 21:00:51 | 2026-10-01 21:09:27 |
| MentoTrading | available | 99 | 2026-10-01 22:56:11 | 2026-10-01 22:56:11 |
| MentoTrading | public | 30 | 2026-10-01 20:59:48 | 2026-10-01 21:00:42 |

### Explicacion del gap entre un run de discover_videos_api.py y el total real
Un run de discover_videos_api.py reporta como `found` lo que `playlistItems().list` devuelve sobre la uploads playlist oficial del canal. Ese endpoint NO incluye contenido con availability fuera de ['available', 'public'] (p.ej. `members_only`): ese contenido es invisible para la API publica sin credenciales de miembro del canal, aunque yt-dlp (discover_videos.py) SI lo encuentra al recorrer el listado general de videos -- solo que no puede descargar su metadata completa, y queda con `processing_status='FAILED'`.

En esta base de datos hay **30** video(s) en esa situacion (ver filas con availability fuera de ['available', 'public'] en la tabla de arriba). Un run de discover_videos_api.py nunca los cuenta en su `found`, pero tampoco los borra ni los duplica -- simplemente nunca aparecen en su enumeracion. Por eso `found` (lo que la API ve) = **732**, mientras que el total real en SQLite (lo que la API ve + lo que yt-dlp encontro pero la API no ve) = **762**.

**762 es la cifra canonica**, verificada arriba por COUNT(DISTINCT video_id) directamente contra SQLite (no un numero recordado de una corrida anterior). Duplicados logicos: 0. Huerfanos: 0. CLASSIFICATION_REPORT.md y MASTER_INDEX.csv son la fuente canonica de aqui en adelante; DISCOVERY_REPORT.md queda como registro historico de una corrida especifica (su `found` nunca pretendio ser el total del proyecto, solo lo que esa corrida en particular vio).

## Total
- TOTAL CANONICO DE VIDEOS UNICOS: 762

## Por canal

| canal | total | public | unlisted | private |
|---|---|---|---|---|
| Gustavom.Trader | 633 | 633 | 0 | 0 |
| MentoTrading | 129 | 129 | 0 | 0 |

## Content format

- LONG_FORM: 170
- SHORT: 417
- LIVE: 173
- CLIP: 0
- UNKNOWN: 2

## Shorts
- SHORTS CONFIRMADOS: 417
- EXCLUIDOS DEL KNOWLEDGE BASE: 417
- SHORTS_IN_KNOWLEDGE_BASE = 0

## Universo candidato para el Segundo Cerebro
- TOTAL = 762
- menos SHORTS = 417
- **CANDIDATOS = 345**

### Por content_format
- videos largos (LONG_FORM): 170
- lives (LIVE): 173
- unknown (UNKNOWN): 2
- CLIP: 0

### Por youtube_privacy_status
- public: 345
- unlisted: 0
- private: 0
- desconocido: 0

## Knowledge base
- Incluidos (include_in_knowledge_base=true): 345
- Excluidos por SHORT confirmado: 417
- Excluidos por otra razon: 0
- Pendientes (content_format=UNKNOWN -- NO excluidos de KB automaticamente, requieren revision): 2

## Revision manual requerida
- Videos con content_format=UNKNOWN, privacy desconocida, o internal_classification=PRIVATE_UNCLASSIFIED: 2

## Videos privados/no-publicos encontrados
- Total: 0

## Evidencia de SHORT y LIVE (pestañas /shorts, /streams vs heuristica)
- SHORT confirmados por pestaña /shorts (yt-dlp, evidencia fuerte): 417
- SHORT detectados solo por heuristica (#shorts/#short en titulo o descripcion, sin confirmacion de pestaña): 0
- LIVE confirmados por pestaña /streams (yt-dlp): 44
- LIVE confirmados solo por la API (liveStreamingDetails, sin estar en /streams): 129
- Discrepancias: video_id en /shorts con duration_sec>180s almacenado (se prioriza la pestaña igual, duration tratada como no confiable aqui): 3
- video_id presentes en /shorts o /streams pero NO encontrados en el discovery principal (uploads playlist / yt-dlp /videos): 1

## Distribucion cronologica por año
- (sin fecha): 30
- 2022: 83
- 2023: 51
- 2024: 187
- 2025: 160
- 2026: 251

