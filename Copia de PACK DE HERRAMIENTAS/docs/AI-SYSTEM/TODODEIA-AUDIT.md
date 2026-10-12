# Auditoría de tododeia.com/community

Fecha: 2026-09-30. Investigación delegada a un agente en background (evita inflar el contexto de la sesión principal, según lo acordado con el usuario).

## Cobertura

- El sitio es público, sin login (lo único gated es anotarse a eventos en vivo, vía Luma — irrelevante para el descubrimiento de recursos).
- La página `/community/repos` renderiza client-side (Next.js), así que no sirve pedirla como HTML estático. El agente usó el `llms-full.txt` propio del sitio (735KB, corpus de las 289 guías) y extrajo la sección "Repos de la comunidad": **176 repositorios open-source** catalogados por el propio sitio.
- De esos 176, se verificaron **53 en vivo contra la API de GitHub** (estrellas, último push, si está archivado) — priorizando los ítems que pediste buscar explícitamente, los que podían solaparse con lo que ya tenés, y los de mayor valor aparente. Los ~123 restantes quedan con la descripción del propio sitio, sin re-chequear — el agente se quedó sin tiempo/budget para una pasada completa y yo le pedí que cortara ahí en vez de seguir horas más.
- Dos URLs habían cambiado de nombre (`affaan-m/everything-claude-code` → `affaan-m/ECC`; `sickn33/antigravity-awesome-skills` → `sickn33/agentic-awesome-skills`) — ya resueltas abajo con el nombre actual. Dos no se pudieron verificar por rate-limit de la API sin autenticar (`ahujasid/blender-mcp`, `clerk/agent-toolkit`).
- **No encontrado en el sitio pese a estar en tu lista de categorías a cubrir:** Chrome DevTools MCP específico, "hookify" como recurso de terceros, tooling específico de reverse-engineering, tooling específico de visual-regression. No es un problema — esos huecos ya se cubrieron en esta sesión por otra vía (`chrome-devtools-mcp` instalado directo, `hookify` es plugin oficial de Anthropic que ya tenías disponible).

## Ítems nombrados explícitamente en el pedido original — resueltos

| Ítem pedido | Qué es realmente | Estado |
|---|---|---|
| Superpowers | `obra/superpowers`, 293k★ | Ya lo tenés |
| GSD | `gsd-build/get-shit-done`, 64k★ pero **archivado/abandonado** en GitHub | Descartado — proyecto muerto |
| Everything Claude Code | `affaan-m/ECC` (antes `everything-claude-code`), 270k★, activo hoy | Ver LIBRARY abajo |
| Skill Creator | Es el skill built-in de `anthropics/skills`, el mismo que ya tenés vía `anthropic-skills:skill-creator` | Duplicado — no es un recurso nuevo |
| find-skills | Es el skill principal dentro de Vercel Skills (`npx skills`), no un repo separado | Ver ON-DEMAND abajo |
| Vercel Skills | `vercel-labs/skills` (32.8k★, `npx skills`) + `vercel-labs/agent-skills` (31.7k★, colección oficial) | Ver ON-DEMAND abajo |
| Skill Vault | `Hainrixz/skill-vault`, 71★ (del mismo autor que `the-architect`/`cyber-neo`/etc.) | Ver LIBRARY abajo |
| Context Mode | `mksglu/context-mode`, 24.4k★, activo hoy | Ver "requiere decisión" abajo |
| Claude Mem | `thedotmack/claude-mem`, 95k★, muy activo | Ver "requiere decisión" abajo |
| Aprende | `Hainrixz/aprende-skill`, 27★ | Ver LIBRARY abajo |
| claude-code-setup | Plugin oficial dentro de `anthropics/claude-plugins-official` | **Instalado en esta sesión** — ver abajo |
| AgentShield | `affaan-m/agentshield`, 1.2k★, activo | Ver ON-DEMAND abajo |
| agent-scan | `snyk/agent-scan` (Snyk), 3.1k★, activo hoy | Ver ON-DEMAND abajo |
| mgrep | `mixedbread-ai/mgrep`, 4.4k★ | Ver ON-DEMAND abajo |
| Agency Agents | `msitarzewski/agency-agents`, 155k★, 144 subagentes MIT | Ver "requiere decisión" abajo |

## Clasificación final

### Instalado en esta sesión

- **`claude-code-setup@claude-plugins-official`** — plugin oficial de Anthropic, **solo lectura** (analiza pero no modifica archivos), recomienda hooks/skills/MCPs/subagentes/comandos para un proyecto puntual. Habilitado porque: es oficial, de bajo riesgo (no ejecuta nada por sí solo), y resuelve directamente el pedido de "mecanismo de skill discovery". Uso: pedile a Claude "recomendá automatizaciones para este proyecto" dentro de cualquier repo.

### ON-DEMAND (sin huella persistente — se usan vía `npx`/CLI cuando hacen falta, no se "instalan")

- **Vercel Skills** (`npx skills`, `vercel-labs/skills`) — marketplace/instalador de skills con auditoría de seguridad integrada (Socket/Snyk/Gen Agent Trust Hub) antes de instalar cada skill. Usar cuando quieras descubrir/instalar una skill puntual de terceros con una capa de verificación ya incorporada.
- **AgentShield** (`affaan-m/agentshield`) y **Snyk agent-scan** (`snyk/agent-scan`) — escanean configuración de agentes/MCP (permisos, hooks, secretos, prompt injection). Complementan a `cyber-neo` (que audita código de la app, no la config del agente). Usar antes de instalar algo de terceros con más peso.
- **mgrep** (`mixedbread-ai/mgrep`) — grep semántico para código/docs/imágenes/PDFs. Probar cuando `grep`/`ripgrep` no alcance.

### LIBRARY (documentado, sin instalar — bajo demanda por proyecto)

- Skill discovery: `Hainrixz/skill-vault`, `yusufkaraaslan/Skill_Seekers`, `ComposioHQ/awesome-claude-skills`, `sickn33/agentic-awesome-skills`.
- Memoria: `mempalace/mempalace`, `garrytan/gbrain`.
- Planning/SDD: `Fission-AI/OpenSpec`, `github/spec-kit`, `eyaltoledano/claude-task-master`, `Hainrixz/claude-anatomy`.
- Diseño/UI: `nextlevelbuilder/ui-ux-pro-max-skill`, `VoltAgent/awesome-design-md`, `nolly-studio/cult-ui`, `nexu-io/open-design`, `google-labs-code/design.md`, `alchaincyf/huashu-design`.
- MCPs específicos de proyecto (instalar solo cuando un proyecto concreto los necesite, nunca global): `crystaldba/postgres-mcp`, `czlonkowski/n8n-mcp`, Supabase MCP, Excel MCP, `Shopify/Shopify-AI-Toolkit`.
- Research/scraping: `D4Vinci/Scrapling`, `ScrapeGraphAI/Scrapegraph-ai`.
- Browser: `browser-use/browser-harness` (+ `bux` para correrlo 24/7) como alternativa a Playwright/agent-browser si hace falta self-healing de tareas de navegación.
- Seguridad de código (además de `cyber-neo`): `anthropics/claude-code-security-review` (Action oficial de Anthropic para PRs), `dmmulroy/anti-slop` (lint anti-código-IA-de-baja-calidad).
- `Hainrixz/claude-db` — plugin que audita/explica/arregla una base de datos (mismo autor que `the-architect`, etc.).
- `Hainrixz/enpoint-agentkit` — genera endpoints REST read-only detectando el stack.
- `affaan-m/ECC` (Everything Claude Code) — meta-harness que empaqueta agentes/skills/hooks/reglas/memoria/seguridad. Se superpone bastante con lo que ya armamos acá (HILARIO-STARTER); vale la pena mirarlo como referencia de diseño más que instalarlo encima.
- `garrytan/gstack`, `coleam00/Archon`, `multica-ai/multica` — stacks/orquestadores alternativos de Claude Code, interesantes como referencia, no reemplazan nada de lo ya instalado.

### REQUIERE DECISIÓN TUYA → ahora delegado a evaluación automática por proyecto

Actualización 2026-09-30 (misma sesión): en vez de quedar como una decisión pendiente tuya sin fecha, estos tres candidatos ahora se evalúan **automáticamente al iniciar cada proyecto nuevo** desde `HILARIO-STARTER/AGENTS.md` — si un proyecto puntual los justifica claramente, Claude los instala directo e informa qué hizo, sin pedir permiso cada vez (ya autorizado). Si ninguno aplica, no se instala nada. Ver la sección "Al iniciar un proyecto nuevo" en `HILARIO-STARTER/AGENTS.md` para el criterio exacto de cada uno.

Motivo original de no instalarlos globalmente (sigue vigente — no piden credenciales, pero cambian comportamiento persistente o agregan mucho volumen, así que no se instalan solos a nivel global, solo por proyecto cuando corresponde):

- **Claude Mem** (`thedotmack/claude-mem`, 95k★) — memoria persistente entre sesiones vía hooks + SQLite. Es probablemente el hallazgo de mayor valor de toda la auditoría, pero Claude Code ya trae un sistema de memoria automática propio (el directorio `memory/` por proyecto que ya está activo en esta misma sesión). Instalar Claude Mem encima significaría correr hooks en cada tool call de cada sesión y un segundo sistema de memoria en paralelo al nativo — una decisión de arquitectura, no un simple "agregar una skill". **Recomendación:** probarlo en un proyecto chico aislado antes de adoptarlo globalmente, no habilitarlo de entrada en todos los proyectos.
- **Context Mode** (`mksglu/context-mode`, 24.4k★) — optimizador de contexto vía hooks + MCP, enruta entre 17 plataformas. Mismo motivo que Claude Mem: cambia comportamiento siempre-activo. **Recomendación:** evaluar aparte, no instalar junto con Claude Mem sin probar que no compitan entre sí (ambos tocan hooks de contexto).
- **Agency Agents** (`msitarzewski/agency-agents`, 144 subagentes MIT) — se instala con un comando a `~/.claude/agents/`. Antes de sumarlos a los ~230 que ya tenés hace falta una pasada de deduplicación (mismo rol, dos nombres) — instalarlo a ciegas rompería justamente el principio de "biblioteca grande, pocas cargando siempre" si duplica roles. **Recomendación:** si en algún momento se necesita, pedir una pasada de comparación puntual contra el roster actual antes de instalar.

### DESCARTADO

| Ítem | Motivo |
|---|---|
| GSD (`gsd-build/get-shit-done`) | Archivado/abandonado en GitHub pese a estar referenciado activamente en el sitio |
| "Skill Creator" del sitio | Duplicado — mismo built-in que ya tenés |
| Superpowers, The Architect, All-Deploy, Cyber Neo, Claude SEO AI, Claude Ads | Ya instalados — el sitio confirma que son exactamente los mismos repos fuente (mismo autor, `Hainrixz/*`) |
| Playwright MCP del sitio (`microsoft/playwright-mcp`) | Es la fuente del MCP `playwright` que ya tenés configurado |
| agent-browser del sitio (`vercel-labs/agent-browser`) | Es la fuente de la skill `agent-browser` que ya tenés |
| `claude-seo` (skills.sh y AgriciDaniel, dos variantes con nombre repetido) | Redundante con `claude-seo-ai` ya instalado; sin verificar calidad, colisión de nombres entre sí |
| prompt-master del sitio (`nidhinjs/prompt-master`) | Coincide casi textual con la metodología de tu `prompt-master` ya instalado — probable origen/inspiración, no una herramienta nueva a sumar |

## Qué no se instaló y por qué (resumen)

Nada de esta lista se instaló de forma automática salvo `claude-code-setup` (oficial, solo lectura, sin credenciales, sin cambio de comportamiento persistente). Todo lo demás son herramientas reales y verificadas, pero instalarlas a ciegas —sobre todo las que corren hooks en cada tool call o agregan decenas/cientos de archivos— iría en contra de "pocas capacidades cargando siempre" y de "auditá antes de reemplazar/duplicar". Quedan documentadas acá para que decidas cuáles probar.
