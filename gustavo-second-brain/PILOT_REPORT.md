# PILOT_REPORT (ronda 2 — post capa de clasificación/gobernanza)

Piloto ejecutado sobre 10 fuentes reales del universo candidato (345 = 762 totales − 417 SHORT), probando el pipeline completo de punta a punta: captions → normalización → chunking → índice → Drive sync → preguntas de calidad.

Selección completa con criterios y razones: `config/pilot_selection.json`. Piloto anterior (ronda 1, previo a la capa de clasificación): `config/pilot_selection_v1_2026-10-01.json`.

## 1. Las 10 fuentes elegidas y por qué

| source_id | canal | título | fecha | duración | formato | topics |
|---|---|---|---|---|---|---|
| YT_CANAL_01_iEOWyJUj95E | MentoTrading | ICT VS CRT ¿Qué estrategia es mejor? | 2025-10-15 | 283s | LONG_FORM | CRT |
| YT_CANAL_01_GNa9yiPfFos | MentoTrading | Paso a paso Estrategia Will Street (CRT) | 2025-08-08 | 1215s | LONG_FORM | CRT |
| YT_CANAL_01_Jhu60-n8gvQ | MentoTrading | Backtesting BIAS en Velas Diarias con CRT | 2025-09-10 | 1355s | LIVE | CRT, bias |
| YT_CANAL_01_0PhgIRQQlZk | MentoTrading | Temporalidades (Curso GRATIS CRT #3) | 2026-08-17 | 832s | LONG_FORM | CRT, timeframe |
| YT_CANAL_01_meWwW8P-Nic | MentoTrading | Bias con estrategia CRT, análisis 30ago26 | 2026-08-30 | 7817s | LIVE | CRT, bias |
| YT_CANAL_02_-7G__mSBIrg | Gustavom.Trader | Guía Gestión de Riesgo (Sharp Shooters) | 2022-10-07 | 1774s | LONG_FORM | riesgo |
| YT_CANAL_02_HgCLgtyxTQE | Gustavom.Trader | Manual de Bias Nasdaq 100 | 2023-06-22 | 611s | LIVE | bias |
| YT_CANAL_02_G8HHJD-m6EM | Gustavom.Trader | Temporalidades Simplificadas | 2024-09-05 | 384s | LONG_FORM | timeframe |
| YT_CANAL_02_kMBBVxNvWuo | Gustavom.Trader | ¿Funciona CRT en Asia? | 2025-12-31 | 762s | LIVE | CRT, Asia |
| YT_CANAL_02_vz9agocN5-Y | Gustavom.Trader | CRT, charla con Geraldin Paternost | 2025-11-08 | 4286s | LIVE | CRT |

Criterios cumplidos: 5/5 por canal, 5 LONG_FORM / 5 LIVE, duraciones de 283s a 7817s, fechas 2022-2026, topics CRT(8) bias(5) timeframe(2) riesgo(1) Asia(1). Ninguna de las 10 se reutilizó del piloto anterior (para ejercitar la cascada de transcripción desde cero, incluyendo el método 1 nuevo).

**Dos criterios no cumplidos, honestamente, por no ser aplicables:**
- **PRIVATE/UNLISTED**: 0 existen en los 345 candidatos (100% PUBLIC, verificado). No se forzó ninguno.
- **Antiguo/reciente dentro de MentoTrading específicamente**: su catálogo candidato solo tiene contenido 2025-2026. La diversidad temporal se cumple en Gustavom.Trader (2022-2025).

## 2. Privacidad

Las 10 fuentes son PUBLIC. `distribution_policy=SHAREABLE`, `allowed_audience` incluye PUBLIC. Ningún archivo privado para ocultar en este piloto — el mecanismo (banner `⚠️ FUENTE PRIVADA / VIP`, supresión de URL) está implementado y testeado en `query.py` y `build_master_index.py`, pero no se ejerció sobre datos reales porque no hay ninguna fuente privada en el universo candidato actual.

## 3. Transcripción

**Cascada usada, los 10 casos:**

| método | cantidad |
|---|---|
| youtube_official (OAuth) | **10/10** |
| yt_dlp_manual | 0 |
| yt_dlp_auto | 0 |
| whisper_local | 0 |

Las 10 fuentes tenían captions oficiales accesibles vía OAuth (primera vez que este método corre contra datos reales — hasta ahora solo estaba testeado con mocks). **El fallback a yt-dlp y Whisper NO se ejerció con datos reales en este piloto** porque no hizo falta — es una limitación honesta a señalar: el camino OAuth está validado end-to-end, yt-dlp (métodos 2-3) y Whisper (método 4) solo están validados por tests unitarios con mocks, no contra un video real sin captions. Si la importación completa encuentra un video sin captions de ningún tipo, ahí se ejercitará Whisper por primera vez contra datos reales.

`transcript_source` quedó registrado para las 10 fuentes (columna `sources.transcript_source` + tabla `transcripts.method`).

## 4. Timestamps

Verificados: los segmentos de cada transcript muestran `start_sec`/`end_sec` crecientes y consistentes con la duración real del video (ej. `meWwW8P-Nic`: duración declarada 7817s, duración real del último segmento 7814.48s). Formato `[HH:MM:SS]` en el Markdown, `start_sec`/`end_sec` numérico en el JSON.

## 5. Calidad de chunks

**179 chunks generados** (ver tabla), ventana de tiempo 60-120s con 10s de overlap (`chunk_content.py`, ya existente, reusado). No son chunks "semánticos" en el sentido de detección de tema/NLP — son ventanas alineadas a los límites de segmento del transcript (nunca cortan a mitad de una oración transcrita), lo cual evita la alternativa real (cortes arbitrarios por bytes). Aclaro esto para no sobre-vender el término: `chunks.topic` queda NULL para los 10, igual que para el resto del catálogo — nadie en el pipeline lo puebla todavía.

| source_id | chunks |
|---|---|
| YT_CANAL_01_iEOWyJUj95E | 3 |
| YT_CANAL_01_GNa9yiPfFos | 11 |
| YT_CANAL_01_Jhu60-n8gvQ | 13 |
| YT_CANAL_01_0PhgIRQQlZk | 8 |
| YT_CANAL_01_meWwW8P-Nic | 72 |
| YT_CANAL_02_-7G__mSBIrg | 16 |
| YT_CANAL_02_HgCLgtyxTQE | 6 |
| YT_CANAL_02_G8HHJD-m6EM | 4 |
| YT_CANAL_02_kMBBVxNvWuo | 7 |
| YT_CANAL_02_vz9agocN5-Y | 39 |

Índice FTS5 (`chunks_search`) reconstruido: 412 chunks totales indexados (179 de este piloto + 233 del piloto anterior, ya existentes en la DB).

## 6. Errores

**3 errores durante la corrida, los 3 causados por el mismo bug, ya corregido:**

`sync_drive.py` extraía el `video_id` desde `source_id` con `rsplit("_", 1)`, que corta mal cuando el video_id de YouTube contiene guiones bajos (ej. `-7G__mSBIrg` se convertía incorrectamente en `mSBIrg`). Afectó a 1 de las 10 fuentes (`YT_CANAL_02_-7G__mSBIrg`: sus 3 archivos reportaron `local_missing`). Corregido con un regex anclado al prefijo fijo `YT_CANAL_NN_` en vez de partir desde la derecha, con 3 tests de regresión nuevos. Re-sincronizada exitosamente después del fix. Los 3 errores se marcaron `resolved=1` en la tabla `errors`.

**0 errores sin resolver.**

## 7. Uso de Whisper

No se ejecutó contra datos reales (ver sección 3) — las 10 fuentes tenían captions oficiales. Validado solo con tests unitarios (mocks), 7/7 pasando, incluyendo el caso de carga perezosa del modelo (no carga el modelo Whisper si no hay nada pendiente de transcribir — bug real encontrado y corregido durante el desarrollo, antes de este piloto).

## 8. Tiempo de procesamiento y espacio utilizado

- **Espacio local** (raw + processed + chunks, 10 videos): **3.9 MB**.
- **Espacio en Drive** (30 archivos: 10×raw, 10×processed, 10×metadata): **~3.88 MB**.
- Sin instrumentación de tiempo por paso (no se midió wall-clock formalmente); los pasos de texto (normalize/chunk/index) son prácticamente instantáneos; `fetch_captions` con OAuth tardó corto por video (llamada API + descarga de un archivo de cientos de KB); Drive sync fue el paso más lento por los reintentos de red, pero sin reintentos reales necesarios (todas las subidas funcionaron al primer intento).

## 9. Sincronización con Drive

**10/10 fuentes, 30/30 archivos verificados con integridad real** (no solo el reporte propio de `sync_drive.py` — hice una verificación independiente después, recalculando el md5 local y volviendo a pedir el md5Checksum a la API de Drive para cada uno de los 30 archivos): **30/30 coinciden**.

Confirmada también la idempotencia real (no simulada): correr `sync_drive.py --pilot` una segunda vez devolvió `already_synced` para los 30 archivos, cero subidas duplicadas.

Estructura usada: `config/drive_structure.json` (ya existente, `00_INDEX/01_RAW/02_PROCESSED/03_METADATA` por canal). RAW nunca se sobreescribe (verificado por diseño + test, ver auditoría de inmutabilidad más abajo).

## 10. Auditoría de inmutabilidad (solicitada antes de correr Drive sync)

Ver mensaje de auditoría completo en la conversación. Resumen:
- **YouTube**: cero llamadas mutadoras en todo el proyecto (`channels/videos/playlistItems/captions().list/download` únicamente).
- **Drive original de Gustavo**: nunca referenciado en ningún script.
- **Drive destino**: solo `create`/`update`, cero `delete`, y `update` solo puede apuntar a archivos que el propio sistema creó (vía tabla `drive_sync`).
- **RAW**: estructuralmente inmutable (el camino de `update` es inalcanzable para `role='raw'`), y el re-fetch está cerrado por `processing_status` salvo `--force` explícito y manual.
- Única excepción transparentada: un archivo de prueba (`_SMOKE_TEST_DELETE_ME.txt`) subido y borrado manualmente por mí para validar que Drive funcionaba, antes de este piloto — no es parte de ningún script.

## 11. query.py nunca usa Shorts como evidencia

Verificado en el código (`WHERE chunks_search MATCH ? AND s.include_in_knowledge_base = 1`, excluye los 417 SHORT por construcción) y con tests (`test_search_excludes_sources_with_include_in_knowledge_base_false`). Las 6 preguntas de este piloto no devolvieron ningún resultado de `content_format=SHORT` (imposible por el filtro).

## 12. Las 6 preguntas de calidad

> La búsqueda indexa TODO lo ya procesado (179 chunks de este piloto + 233 del piloto anterior) — es el comportamiento correcto para un buscador real, no artificialmente restringido a las 10 de hoy. Marco con 🆕 los resultados que vienen de este piloto.

**1. ¿Cómo define Gustavo el bias diario?** — 5 resultados.
- `Cómo Dominar el BIAS y DOL Diario...` (Gustavom.Trader, 2026-05-18) @ 00:00:00 — source_id=YT_CANAL_02_NeK0B7tN7ZM
- `Nunca nadie te lo explico bien...` (MentoTrading, 2026-09-26) @ 00:05:33 — source_id=YT_CANAL_01_bDVDNGW8IIE
- 🆕 `Bias con estrategia CRT, análisis 30ago26` (MentoTrading, 2026-08-30) @ 01:28:58 — source_id=YT_CANAL_01_meWwW8P-Nic — PUBLIC, deep link disponible.

**2. ¿Qué dice Gustavo sobre sobreoperar?** — 5 resultados, todos de `El SECRETO para GANAR SIEMPRE en el TRADING` (MentoTrading, piloto anterior) en distintos timestamps (00:05:30, 00:09:10, 00:11:00...).

**3. ¿Qué timeframe mira primero?** — 5 resultados.
- 🆕 `Temporalidades Simplificadas...` (Gustavom.Trader, 2024-09-05) @ 00:03:39 — source_id=YT_CANAL_02_G8HHJD-m6EM — PUBLIC.
- Resto: `Aprende TRADING desde CERO` (piloto anterior, 2024-11-30).

**4. ¿Qué dice Gustavo sobre operar Asia?** — 4 resultados (el gate de relevancia descartó un 5to candidato por no alcanzar el umbral de evidencia — comportamiento esperado, no forzado).
- 🆕 `Backtesting BIAS en Velas Diarias con CRT` (MentoTrading, 2025-09-10) @ 00:11:03 — source_id=YT_CANAL_01_Jhu60-n8gvQ.
- 🆕 `CRT, charla con Geraldin Paternost` (Gustavom.Trader, 2025-11-08) @ 00:10:59 — source_id=YT_CANAL_02_vz9agocN5-Y.

**5. ¿Qué diferencia plantea entre método y estrategia?** — 5 resultados.
- 🆕 `CRT, charla con Geraldin Paternost` @ 00:14:39 — source_id=YT_CANAL_02_vz9agocN5-Y.
- Resto: piloto anterior.

**6. ¿Qué dice Gustavo sobre gestión de riesgo?** — 5 resultados, todos de `Aprende TRADING desde CERO` (piloto anterior, video de 4.5hs). Ninguno de este piloto entró en el top-5 para esta pregunta específica, aunque `-7G__mSBIrg` (Guía Gestión de Riesgo, 2022) sí fue procesado — su contenido no superó el ranking BM25 + gate de relevancia frente al video más largo del piloto anterior. No es un error: es el buscador priorizando por relevancia real, no por favoritismo hacia lo más nuevo.

Todos los resultados: `is_public=True`, sin advertencia de privacidad (coherente con que las 10 fuentes son PUBLIC).

## 13. Contradicciones temporales

Revisé manualmente los fragmentos de las preguntas con mayor dispersión de fechas (bias: 2025-2026, timeframe: 2024-2026). **No detecté ninguna contradicción factual clara** entre contenido antiguo y reciente en esta muestra — los fragmentos son consistentes temáticamente (conceptos de estructura de mercado, CRT, bias). No me pareció correcto forzar un `potential_conflict=true` artificial solo para cumplir el checklist cuando la evidencia no lo respalda. El mecanismo (`sources.potential_conflict`, tabla `source_relations` con `conflicts_with`/`supersedes`) existe, está migrado y listo — simplemente no se activó porque no encontré evidencia real de conflicto en este lote.

## 14. Problemas pendientes

- El fallback a yt-dlp (métodos 2-3) y a Whisper (método 4) no se validaron contra datos reales en este piloto — solo con tests. Riesgo bajo (son los métodos ya usados exitosamente en el piloto anterior y en desarrollo), pero no "probados en producción" todavía.
- `chunks.topic` sigue sin poblarse (ni en este piloto ni en el anterior) — si se quiere búsqueda filtrada por tema, falta ese trabajo.
- El buscador mezcla resultados de ambos pilotos sin distinguir "ronda" — es el comportamiento correcto para un buscador real, pero quería señalarlo explícitamente ya que este reporte sí distingue con 🆕.

## 15. PILOT_READY

**PILOT_READY = TRUE**

### Estimación para importar las ~345 fuentes reales restantes

- **Universo real a procesar**: 345 fuentes (170 LONG_FORM + 173 LIVE + 2 UNKNOWN), **206.4 horas** de contenido total, promedio 36 min/video.
- **Método de transcripción esperado**: si la tasa de éxito de captions oficiales se mantiene (10/10 en este piloto, aunque la muestra es chica), la gran mayoría debería resolverse por `youtube_official` sin necesitar Whisper. **No puedo garantizar esto con el mismo nivel de confianza para las 345** -- 10 es una muestra pequeña y no incluye necesariamente los casos más antiguos/oscuros del catálogo.
- **Almacenamiento estimado**: ~3.88 MB / 5.37 horas de este piloto ⇒ aproximadamente **150-200 MB totales** (texto puro, no audio/video -- footprint liviano incluso a escala completa).
- **Tiempo estimado**: sin instrumentación de tiempo real por video, la estimación es de orden de magnitud, no precisa. Si la mayoría usa captions (rápido, segundos por video), el cuello de botella pasa a ser la API de YouTube (cuota, rate limiting) y Drive (red). Si una fracción significativa necesita Whisper (minutos por hora de audio en CPU), el tiempo total podría crecer sustancialmente -- esto es la principal incógnita antes de lanzar la importación completa.

No se lanzó la importación masiva. Queda pendiente tu aprobación explícita.
