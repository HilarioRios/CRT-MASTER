# HILARIO AI DEV SYSTEM — diseño

Fecha: 2026-09-30
Estado: aprobado por el usuario (con la condición GLOBAL vs HILARIO-STARTER)

## Objetivo

Convertir `/Users/hilario/Downloads/Claude/Replica` en el repositorio meta ("HILARIO AI DEV SYSTEM") que documenta y organiza:

1. **GLOBAL** (`~/.claude`): el taller completo — hooks de seguridad reales, MCPs útiles sin credenciales pendientes, y todo lo que ya estaba instalado (prompt-master, skill-router, Superpowers, the-architect, cyber-neo, all-deploy, claude-seo-ai, claude-ads, ~230 agentes, ~65 skills de marketing, Playwright MCP, marketplace oficial `claude-plugins-official` ya conocido).
2. **HILARIO-STARTER/** (carpeta portable dentro de este repo): la "mochila" que se copia a cada proyecto nuevo — `AGENTS.md`, `CLAUDE.md`, `.claude/rules/`, reglas de `hookify` (guardrails de proyecto), y punteros a skills/agentes globales (sin duplicarlos).

No se toca nada de lo ya instalado sin necesidad. Todo lo que requiera login/API key/gasto queda marcado "REQUIERE ACCIÓN DE HILARIO" y no se activa solo.

## Hallazgos clave de la auditoría (no repetir instalación)

- Ya existen globalmente: `prompt-master`, `skill-router`, Superpowers completo, `the-architect`, `cyber-neo`, `all-deploy`, `claude-seo-ai`, `claude-ads`, ~65 skills de marketing, ~230 agentes especialistas, MCP `playwright`, skills "core" del producto (code-review, security-review, update-config, workflow-authoring, skill-creator, etc.), y un marketplace oficial ya añadido (`claude-plugins-official`, repo `anthropics/claude-plugins-official`) con plugins conocidos pero **sin habilitar**: `hookify`, `github`, `context7`, `security-guidance`, `code-review` (duplicado del core), `skill-creator` (duplicado), varios LSP, `pr-review-toolkit`, `commit-commands`, etc.
- **Hueco real de seguridad**: no hay ningún hook configurado y `~/.claude/settings.json` tiene `permissions.allow: ["Bash(*)", "Read(*)", "Edit(*)", "Write(*)"]` — o sea, ningún comando de shell pide confirmación. Un hook es el único freno real posible.
- `hookify` (oficial, Anthropic) es determinístico (regex sobre `tool_input`, sin llamadas a LLM) y su `action: block` sí produce `hookSpecificOutput.permissionDecision: "deny"` → bloqueo real. Pero **sus reglas se cargan con un glob relativo al cwd** (`.claude/hookify.*.local.md`), no desde `~/`. Por eso no alcanza por sí solo como red de seguridad global: solo protege proyectos que ya tengan esos archivos.
- Por eso: dos capas.
  1. Hook global hecho a mano en `~/.claude/hooks/guard-dangerous-bash.sh`, registrado directo en `~/.claude/settings.json` → protege CUALQUIER proyecto, tenga o no `.claude/hookify.*.local.md`. Sin dependencias nuevas (usa `jq`, ya presente).
  2. Plugin `hookify` habilitado globalmente + archivos `hookify.*.local.md` incluidos dentro de `HILARIO-STARTER/.claude/` → cada proyecto nuevo clonado del starter trae reglas visibles, editables, sin código oculto.
- `claude` CLI 2.1.285 confirmado con `claude mcp add` y `claude plugin enable/disable`. `jq`, `python3`, `node` v22, `npx`, `gh` (autenticado como HilarioRios) ya están disponibles localmente.
- `chrome-devtools-mcp` es un paquete npm oficial del equipo de Chrome DevTools (Google), sin credenciales, se agrega con `claude mcp add chrome-devtools --scope user -- npx chrome-devtools-mcp@latest`. Hoy solo existe Playwright MCP — esto llena el hueco de "Chrome DevTools" pedido.
- `context7` (MCP de docs/librerías) funciona sin API key (header `Authorization` con default vacío) — se puede habilitar ya.
- `github` (MCP oficial) **requiere `GITHUB_PERSONAL_ACCESS_TOKEN`** vía header Authorization — aunque `gh` ya está logueado, usar ese token para un MCP nuevo es "conectar una cuenta" y el usuario pidió confirmación explícita antes de eso. Queda documentado y listo para un solo comando, pero no se activa solo.
- Esta carpeta (`Replica`) no es un repo git. Se inicializa git local (reversible) para que el starter tenga historial.

## Arquitectura de carpetas

```
Replica/                                  (repo meta, git-init)
├── README.md
├── docs/
│   ├── superpowers/specs/2026-09-30-hilario-ai-dev-system-design.md   (este archivo)
│   └── AI-SYSTEM/
│       ├── README.md
│       ├── INSTALLED.md      (tabla completa: nombre/tipo/fuente/URL/scope/categoría/estado/modo/qué hace/cuándo/dependencias/conflictos/razón/fecha)
│       ├── SKILLS.md
│       ├── AGENTS.md         (roster completo + subconjunto CORE)
│       ├── PLUGINS.md
│       ├── MCPS.md
│       ├── HOOKS.md
│       ├── ROUTING.md
│       ├── SECURITY.md
│       ├── UPDATING.md
│       └── TROUBLESHOOTING.md
├── HILARIO-STARTER/                       (la mochila portable)
│   ├── README.md / install.sh
│   ├── AGENTS.md              (chico: routing, seguridad, workflow, done-criteria)
│   ├── CLAUDE.md               (adaptado de CLAUDE.base.md existente)
│   └── .claude/
│       ├── rules/               (convención oficial .claude/rules/*.md)
│       │   ├── security.md
│       │   ├── working-contract.md
│       │   └── web-defaults.md  (path-scoped a frontend)
│       ├── hookify.block-dangerous-rm.local.md
│       ├── hookify.block-force-push.local.md
│       ├── hookify.block-reset-hard.local.md
│       ├── hookify.block-drop-database.local.md
│       ├── hookify.warn-env-files.local.md
│       ├── agents/README.md    (puntero al roster global, sin duplicar)
│       └── skills/README.md    (puntero al roster global, sin duplicar)
└── Copia de agentes y skilss/             (preservada intacta, documentada como predecesora)
```

Global (`~/.claude`, fuera de este repo, se documenta pero no se versiona aquí):
- `hooks/guard-dangerous-bash.sh` (nuevo)
- `settings.json` → agrega bloque `hooks.PreToolUse`, agrega `hookify`, `context7` a `enabledPlugins` (github queda documentado, no habilitado)
- `~/.claude.json` → agrega MCP `chrome-devtools`

## Fases de implementación

1. Hooks de seguridad global (hand-written + hookify plugin habilitado).
2. HILARIO-STARTER completo (git init del repo, estructura de carpetas de arriba).
3. MCPs sin credenciales (chrome-devtools, context7); github documentado como pendiente.
4. Cruce del inventario ya reunido por el agente de research de tododeia.com/community contra lo instalado, clasificación CORE/STARTER/ON-DEMAND/LIBRARY/DESCARTADO con motivo.
5. docs/AI-SYSTEM completo + verificación final (JSON válido, hook ejecuta, sin referencias rotas) + informe de 20 puntos.

## Fuera de alcance (por ahora, documentado como LIBRARY u opcional)

- Habilitar en bloque los ~20 plugins restantes de `claude-plugins-official` (LSPs de lenguajes no usados, `ralph-loop`, `mcp-tunnels`, plugins de demo). Quedan documentados como disponibles en el marketplace ya conocido, activables bajo demanda.
- `security-guidance` (hace llamadas a un `review_api`/LLM por diff; se solapa con `cyber-neo` + skill `security-review` ya activa) — queda como LIBRARY, no CORE, para no cargar algo con costo/latencia adicional por defecto.
- MCPs con credenciales pendientes (github, ahrefs, amplitude, canva, figma, klaviyo, notion, similarweb, slack, supermetrics) — documentados, no conectados.

## Riesgos y mitigaciones

- Falsos positivos del hook global → patrones acotados (ej. `rm -rf node_modules` sigue permitido; solo se bloquean rutas anchas/raíz y comandos explícitamente destructivos de la lista del usuario).
- Doble capa de hooks (global + hookify) podría parecer redundante → documentado explícitamente en HOOKS.md como defensa en profundidad, no conflicto (ambos solo deniegan, nunca se pisan).
- No se modifica `Copia de agentes y skilss/` para no romper nada existente; se referencia desde la documentación como predecesora de HILARIO-STARTER.
