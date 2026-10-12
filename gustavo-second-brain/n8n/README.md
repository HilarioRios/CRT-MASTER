# n8n Community — instalación local

Instalación local de n8n (self-hosted, Docker), adelantada respecto al resto del plan del proyecto
(FASE 14/27). Por ahora es solo infraestructura: **no hay workflows productivos cargados** y no
orquesta todavía el pipeline Python (FASE 0-13), que sigue corriendo de forma independiente y no
fue tocado por esta instalación.

## Qué es esto

- n8n Community corriendo en un contenedor Docker, expuesto **únicamente en `http://localhost:5678`**.
- El puerto se publica como `127.0.0.1:5678:5678`, no `0.0.0.0`, así que no es alcanzable desde la
  red local ni desde internet.
- Datos persistentes (workflows, credenciales, DB interna de n8n) en el volumen nombrado
  `gustavo_n8n_data`. Sobrevive a `docker compose restart`, `stop`/`start` y `docker compose down`
  (sin `-v`). Solo `docker compose down -v` lo borraría.
- Timezone del contenedor: `America/Montevideo`.
- La DB interna de n8n (SQLite dentro del volumen `gustavo_n8n_data`) es independiente de
  `database/gustavo_brain.sqlite` del proyecto. No se comparte ni se monta ningún volumen del
  proyecto dentro de este contenedor.

## Primer uso

```bash
cd n8n
cp .env.example .env   # ya existe un .env real generado para este setup; no hace falta recrearlo
docker compose up -d
```

Abrir http://localhost:5678 en el navegador. **Paso manual pendiente:** la primera vez pide crear
la cuenta "owner" propia de n8n (nombre, email, contraseña) — eso lo maneja n8n mismo, no este
`docker-compose.yml`, así que no se puede automatizar sin que lo hagas vos.

Nota: se probó `N8N_BASIC_AUTH_ACTIVE` y resultó ser un no-op en esta versión de n8n (2.41.5) — ya
fue reemplazada por el sistema de cuentas propio. Por eso no está en el `docker-compose.yml` final.
El control de acceso real de esta instalación es: (1) el puerto solo escucha en `127.0.0.1`, y
(2) la cuenta owner que crees en el primer login.

## Comandos útiles

```bash
docker compose ps                 # estado del contenedor
docker compose logs -f n8n        # logs en vivo
docker compose restart            # reinicia manteniendo los datos
docker compose stop               # detiene sin borrar nada
docker compose down               # elimina el contenedor, conserva el volumen (datos intactos)
docker compose down -v            # ¡BORRA el volumen y todos los datos de n8n! No usar sin querer hacerlo.
```

## Workflow de orquestación (borrador, INACTIVO)

`n8n/workflows/orchestrate_pipeline.json` — preparado en paralelo mientras corría la importación
masiva, a pedido explícito. Importado dentro del contenedor (`n8n import:workflow`), **queda
inactivo** (confirmado vía `n8n export:workflow` → `"active": false`). Nadie lo ejecutó.

Estructura (4 nodos, secuencial):
1. **Schedule (placeholder)** — Cron diario a las 06:00, sin activar. Revisar la frecuencia real
   antes de habilitar.
2. **Check for new videos** — `Execute Command` que corre `scripts/discover_videos_api.py`
   (solo lectura contra la YouTube Data API, idempotente, no descarga nada).
3. **Run pipeline** — `Execute Command` que corre `scripts/run_pipeline.py`, que ya incluye
   fetch/transcribe/normalize/chunk/index/sync-a-Drive internamente (no se duplicó esa lógica
   acá, se reusa el script tal cual).
4. **Done** — nodo `NoOp`; el log real es el historial de ejecuciones de n8n.

Ningún nodo tiene credenciales de n8n conectadas — los `Execute Command` corren los scripts
Python del proyecto, que leen su propio `.env` de la raíz del proyecto (no el de n8n). Nada de
YouTube/Drive se tocó desde n8n.

**Para activarlo en algún momento**: abrir el workflow en la UI, revisar el cron del nodo 1,
y recién ahí togglear "Active". No se activa solo ni con un restart del contenedor.

## Alcance explícito de esta instalación

- Se creó un workflow (ver arriba), pero queda **inactivo** y sin ejecutar.
- No se conectó ninguna credencial (YouTube, Drive, etc.) dentro de n8n.
- No se modificó el pipeline Python, la base `database/gustavo_brain.sqlite`, ni ningún proceso
  que ya estuviera corriendo.
- Existe también un `docker-compose.yml` en la raíz del proyecto, scaffolding de una sesión
  anterior para la misma idea (ver `SETUP_STATUS.md`). Este `n8n/docker-compose.yml` es el que se
  usó para esta instalación local y es autosuficiente (no depende del `.env` de la raíz del
  proyecto, que contiene credenciales de otros servicios). El de la raíz quedó sin usar; se puede
  eliminar o consolidar más adelante sin impacto porque no hay ningún contenedor corriendo a partir
  de él.
