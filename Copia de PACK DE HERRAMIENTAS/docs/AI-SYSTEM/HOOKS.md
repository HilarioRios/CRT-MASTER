# Hooks — guardrails reales

## Por qué dos capas

`~/.claude/settings.json` tiene `permissions.allow: ["Bash(*)", "Read(*)", "Edit(*)", "Write(*)"]` — ningún comando de shell pide confirmación. Sin un hook, no hay freno real ante `rm -rf`, `git push --force`, `DROP DATABASE`, etc.

El plugin oficial `hookify` es determinístico (regex sobre `tool_input`, sin llamadas a LLM) y su `action: block` sí produce un bloqueo real (`hookSpecificOutput.permissionDecision: "deny"`). Pero carga sus reglas con un glob **relativo al directorio de trabajo** (`.claude/hookify.*.local.md`), no desde `~/`. Por eso solo protege proyectos que ya tengan esos archivos — no es una red de seguridad global por sí sola.

Por eso:

1. **Capa 1 — hook global hecho a mano** (`~/.claude/hooks/guard-dangerous-bash.sh`, registrado en `~/.claude/settings.json` bajo `hooks.PreToolUse`): protege **cualquier** proyecto, exista o no `.claude/hookify.*.local.md`. Sin dependencias nuevas (usa `jq`, ya presente en la máquina).
2. **Capa 2 — plugin `hookify` habilitado globalmente + reglas dentro de `HILARIO-STARTER/.claude/`**: cada proyecto nuevo clonado del starter trae reglas visibles y editables en Markdown, sin tocar JSON.

Las dos capas solo **deniegan**, nunca se pisan entre sí — no hay conflicto posible, es defensa en profundidad.

## Capa 1 — patrones bloqueados por el hook global

Archivo: `~/.claude/hooks/guard-dangerous-bash.sh`. Antes de evaluar cualquier patrón, el script le quita comillas, backticks, backslashes y paréntesis al comando (**no** el símbolo `$`, para no romper la detección de `$HOME`) — así un path entre comillas, un `sh -c`/`bash -c`/`eval` que envuelva el comando peligroso, una sustitución de comando con backticks o `$(...)`, o un path con barra escapada, se detectan igual que la forma "limpia".

Bloquea (case-insensitive donde aplica):

- `rm -rf` / `rm -fr` sobre una ruta que, **después de quitar comillas**, sea exactamente `/`, `~`, `$HOME` (con o sin `/` final), o esas rutas con `*` al final. **No bloquea** `rm -rf node_modules`, `rm -rf ./dist`, ni ninguna otra ruta absoluta que no sea exactamente `/`/`~`/`$HOME` (ej. `rm -rf /Users/otra-cosa` **no** se bloquea — ver "Alcance deliberadamente limitado" abajo).
- `git push --force`, `--force-with-lease`, `-f` — pero no una rama cuyo nombre simplemente empiece con `--force-` (eso no es un flag).
- `git reset --hard`.
- `git clean -fd` (y variantes `-fdx`, `-df`).
- `DROP DATABASE` / `DROP TABLE` (cualquier cliente SQL).
- Comandos de migración conocidos como destructivos: `prisma migrate reset`, `rails db:drop`, `knex migrate:rollback --all`, `alembic downgrade base`.
- Sobrescritura (`>`) de un `.env` real, con o sin ruta por delante (`> .env`, `> ./config/.env`, `> /abs/path/.env`) — no bloquea `.env.example`, `.env.sample`, `.env.template`.
- `rm` de un `.env` real, bare o con ruta por delante.
- `git add` / stage de un `.env` real, bare o con ruta por delante.

### Alcance deliberadamente limitado

El guard de `rm -rf` solo reconoce como "raíz/home" los tokens literales `/`, `~`, `$HOME` — no cualquier ruta absoluta "importante". Ampliarlo a bloquear, por ejemplo, `rm -rf /Users/hilario/proyecto-importante` requeriría una lista explícita de rutas a proteger (no hay forma genérica de saber qué ruta absoluta es "importante" sin generar falsos positivos constantes). Si necesitás proteger una ruta específica, agregá un patrón dedicado para esa ruta exacta.

**Límite inherente (no solucionable con regex estático):** el script normaliza texto, no ejecuta ni resuelve nada. Una sustitución de comando cuyo resultado no aparece literalmente en el texto del comando (ej. `rm -rf $(dirname ../../../..)`, o cualquier construcción que arme la ruta peligrosa en tiempo de ejecución en vez de escribirla) **no** se detecta, porque en el momento del chequeo ese texto todavía no se evaluó. Resolverlo de verdad requeriría un parser de shell completo (o ejecutar el comando en un sandbox antes de decidir, lo cual tiene sus propios riesgos) — fuera de alcance para un hook liviano. Esto es una limitación conocida y aceptada, no un descuido.

### Cómo agregar/cambiar un patrón

Editar `~/.claude/hooks/guard-dangerous-bash.sh`, agregar o ajustar un bloque `if ... grep -qE ... ; then deny "..."; fi`, y correr `bash docs/AI-SYSTEM/hooks-regression-test.sh` antes de confiar en el cambio — ese script queda commiteado en el repo justamente para volver a correrlo cada vez.

## Capa 2 — reglas de `hookify` en HILARIO-STARTER

Archivos en `HILARIO-STARTER/.claude/`:

- `hookify.block-dangerous-rm.local.md`
- `hookify.block-force-push.local.md`
- `hookify.block-reset-hard.local.md`
- `hookify.block-drop-database.local.md`
- `hookify.warn-env-files.local.md` (este solo **avisa**, no bloquea — editar `.env` a veces es legítimo)

Formato: frontmatter YAML (`name`, `enabled`, `event: bash|file`, `pattern` o `conditions`, `action: warn|block`) + cuerpo Markdown con el mensaje que ve el usuario. Referencia completa: `/hookify:help` o el `SKILL.md` de `writing-rules` dentro del plugin.

**Importante:** estas reglas solo se evalúan si el plugin `hookify` está habilitado (ya lo está, a nivel `user` — ver `PLUGINS.md`) y si el directorio de trabajo actual tiene esos archivos `.claude/hookify.*.local.md` (por eso viven en `HILARIO-STARTER`, para que viajen a cada proyecto nuevo).

**Gap conocido en la Capa 2:** `hookify.block-force-push.local.md` recibió el mismo fix que la Capa 1 (el flag `--force` ya no matchea un nombre de rama que empiece con `--force-`). `hookify.block-dangerous-rm.local.md` **todavía tiene el patrón viejo** (no reconoce `rm -rf "/"` entre comillas ni `rm -rf ~/` con barra final) — un intento de corregirlo en esta sesión fue bloqueado por el clasificador de auto-mode de la plataforma (denegó la edición del archivo, ver `TROUBLESHOOTING.md`). No es un hueco de seguridad real porque la **Capa 1 ya cubre estos casos globalmente, en cualquier proyecto**, incluidos los que usan este starter — pero si querés paridad entre las dos capas, aplicá manualmente este cambio de una línea en `HILARIO-STARTER/.claude/hookify.block-dangerous-rm.local.md`:

```diff
-pattern: rm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|~|\$HOME)(\s|\*?\s*$|$)
+pattern: rm\s+-[a-z]*r[a-z]*f[a-z]*\s+["']?(/|~|\$HOME)/?["']?(\s|\*|["']|$)
```

## Cómo se verificó

1. Batería de regresión commiteada en `docs/AI-SYSTEM/hooks-regression-test.sh` (40 casos) — corré `bash docs/AI-SYSTEM/hooks-regression-test.sh` para volver a verificar en cualquier momento. Resultado actual: 40/40 pasan. Incluye los 21 casos originales, 15 del primer pase de code review (comillas, `sh -c`/`bash -c`/`eval`, rutas con prefijo para `.env`, nombre de rama que no es un flag), y 4 de un segundo pase de re-verificación independiente (backticks, `$(...)`, barra escapada, y una ruta dinámica que debe seguir permitida).
2. Dos rondas de code review independiente (subagentes separados, sin ver el trabajo del otro): la primera encontró los bugs de comillas/`.env`; la segunda re-verificó esos fixes de forma independiente (no solo corriendo la batería commiteada, con sus propios casos adicionales) y encontró el gap de sustitución de comandos, que también se corrigió. Veredicto final de la segunda ronda: "Ready to merge: Yes".
3. Se probó en vivo, dentro de esta misma sesión, corriendo comandos reales a través del Bash tool (no solo el script standalone): `git reset --hard HEAD` en un repo descartable (antes del fix), y un `rm -rf` sobre `/` entre comillas reales (después del fix) — ambos bloqueados correctamente.

## Falsos positivos conocidos (y por qué no se evitan)

- Un commit cuyo mensaje contenga la palabra ".env" pero no toque el archivo no se bloquea (el chequeo es sobre `git add`/`git commit -am` del path, no del texto del mensaje) — comportamiento correcto, no un bug.
- Un `DROP TABLE` dentro de un string literal que no se ejecuta (por ejemplo, un comentario en un archivo que se está mostrando con `cat`) **si** se pasa como argumento de un comando Bash, igual se bloquea — es una limitación intencional: el hook no distingue "se va a ejecutar" de "se va a imprimir". Si esto molesta en un caso legítimo, correlo manualmente fuera de Claude Code.
- Pasó en la construcción de este mismo sistema: un mensaje de commit que describía en texto plano el fix de `rm -rf` quedando quoteado (escribiendo el patrón peligroso real dentro del mensaje) fue bloqueado por el propio hook al intentar commitear — mismo motivo que el punto anterior. Solución: describir el patrón sin escribirlo literalmente (como se hizo en el mensaje de commit real de ese fix), o commitear manualmente fuera de la sesión.
