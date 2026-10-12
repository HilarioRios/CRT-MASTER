# FULL_IMPORT_REPORT

Reconciliado 2026-10-02 contra SQLite como fuente de verdad (hubo una versión previa de este
archivo, escrita por otra sesión en paralelo, con una afirmación que no coincidía con la base de
datos — ver sección 1). Verificado: ningún otro proceso tenía el archivo abierto ni lo había
tocado en los últimos 20+ minutos antes de esta escritura.

## Totales (SQL, verificado ahora mismo)

| métrica | valor |
|---|---|
| TOTAL elegible (`include_in_knowledge_base=1`) | **345** |
| TOTAL exitoso (`DRIVE_SYNCED`) | **314** |
| TOTAL failed | **31** |
| — de los cuales, exclusivos de membresía paga (`YOUTUBE_MEMBERS_ONLY_EXCLUSIVE`) | **30** |
| — de los cuales, bug técnico aislado (no membresía) | **1** (`YT_CANAL_01_cSOcOpJvMS8`, en reprocesamiento, ver sección 2) |
| TOTAL Shorts excluidos (permanentemente, `SHORTS_IN_KNOWLEDGE_BASE=0`) | **417** |
| TOTAL chunks | **5,515** |
| TOTAL horas de contenido procesado (314 fuentes) | **165.3 horas** |
| TOTAL captions oficiales (OAuth) | **38** |
| TOTAL yt-dlp auto | **276** |
| TOTAL Whisper (primera pasada) | **0** |

## 1. Corrección respecto a la versión previa de este reporte

Una versión anterior de este archivo (escrita por otra sesión de Codex corriendo en paralelo)
afirmaba: *"las 31 fuentes FAILED son, sin excepción, videos solo-para-miembros pagos"*. Verificado
contra la tabla `errors` fuente por fuente: **30 de 31** tienen `stage='discovery'` con el mensaje
*"Requires paid YouTube channel membership..."* — confirmado membresía paga, correcto. La fuente
restante, `YT_CANAL_01_cSOcOpJvMS8` (canal MentoTrading, no Gustavom.Trader — ya es una señal de
que no pertenece al mismo grupo), tiene en cambio 3 entradas `stage='pipeline'` con el mensaje
`open() got an unexpected keyword argument 'metadata_errors'` — un error de código/dependencia,
nada que ver con membresía. Ese dato ya quedó etiquetado en SQLite
(`sources.internal_classification = 'YOUTUBE_MEMBERS_ONLY_EXCLUSIVE'` para las 30 confirmadas,
NULL para la 1 que no aplica).

## 2. Bug técnico encontrado, corregido y en reprocesamiento

**Causa raíz**: `faster-whisper==1.2.1` llama internamente a `av.open(..., metadata_errors="ignore")`.
El entorno tenía instalado `av==19.0.0` (sin pin explícito en `requirements.txt` — venía como
dependencia transitiva, `faster-whisper` solo pide `av>=11`), y PyAV eliminó ese kwarg de
`open()` en algún punto después de la v18. Reproducido y confirmado con un test aislado
(`TypeError: open() got an unexpected keyword argument 'metadata_errors'`).

**Corrección aplicada**:
- `pip install "av==18.1.0"` (última versión con wheel prebuilt para este entorno — macOS
  arm64/Python 3.14 — que todavía acepta `metadata_errors`; 19.0.0 es la primera que lo rompe).
- Confirmado con el mismo test: ya no lanza `TypeError`.
- `requirements.txt` actualizado con `av<19` y un comentario explicando el motivo, para que no
  reaparezca en una instalación futura.

**Reprocesamiento**: lancé `process_source()` (la misma función del pipeline, sin reimplementar
nada) únicamente sobre `YT_CANAL_01_cSOcOpJvMS8`, en background — **todavía corriendo** al momento
de escribir este reporte (cayó a Whisper local, que es CPU-bound y lento). Actualizaré este
archivo con el resultado final cuando termine.

## 3. Los 30 exclusivos — intento de acceso vía OAuth de propietario

Siguiendo instrucción explícita: **solo OAuth de Gustavo como dueño/admin de canal, cero cookies,
cero contraseñas, cero sesión de navegador, solo operaciones READ-ONLY.**

**Resultado: BLOQUEADO antes de poder intentar ninguno de los 30 — cuota de la YouTube Data API
agotada.**

Probé contra el primero de los 30 (`6czpwpXeKdA`), con el token OAuth del propio canal
Gustavom.Trader (`tokens/youtube_gustavo_trader.json`, ya autorizado, sin tocar nada nuevo):

```
videos().list(part="status,snippet", id=...)  -> HttpError 403: "exceeded your quota"
captions().list(part="snippet", videoId=...)  -> HttpError 403: "exceeded your quota"
```

Esto es un error a nivel de cuota del proyecto/API, no del video puntual — no tiene sentido
reintentar los otros 29, van a fallar igual. Me detuve ahí, tal como pediste.

**Por qué pasó**: la corrida completa de ayer ya había consumido ~9,500 de las 10,000 unidades
diarias en los 38 videos que sí lograron `youtube_official` (captions cuestan 50 por `list` + 200
por `download` ≈ 250/video). La cuota de YouTube Data API resetea a medianoche **hora del
Pacífico (EE.UU.)**, no hora local — ahora mismo acá son las 00:57 (Montevideo, UTC-3) = 20:57 del
1-oct (Pacífico, UTC-7). El reset cae aproximadamente a las **~04:00 hora de Montevideo**.

```
MEMBERS_ONLY_TOTAL: 30
ACCESIBLES_CON_OAUTH: 0
CON_CAPTIONS: 0
SIN_CAPTIONS: 0
NO_ACCESIBLES: 30 (bloqueados por cuota, no por permiso del video en sí)
ERRORES: 1 tipo de error, repetido -- HttpError 403 "quotaExceeded" (YouTube Data API), en
  videos().list y en captions().list, con el token OAuth de Gustavom.Trader
```

**Siguiente paso sugerido** (no ejecutado, a la espera de tu señal): reintentar los 30 después de
~04:00 hora local, cuando la cuota resetee. En ese momento SÍ vale la pena probar cada uno
individualmente, porque "membresía paga para el público" y "acceso del dueño vía OAuth" son cosas
distintas — el dueño del canal típicamente puede ver metadata/captions de su propio contenido
aunque esté restringido para espectadores, pero eso recién se puede confirmar con cuota
disponible.

## 4. Shorts

**SHORTS_IN_KNOWLEDGE_BASE = 0**, sin cambios desde el primer chequeo.

## KNOWLEDGE_BASE_READY = TRUE

314 de 345 fuentes elegibles (91.0%) completamente procesadas e indexadas. De las 31 restantes: 30
son contenido de membresía paga de YouTube (clasificado y documentado, pendiente de reintento de
OAuth cuando la cuota resetee — no bloquea el resto del catálogo), y 1 es un bug de dependencia ya
corregido, con reprocesamiento en curso.
