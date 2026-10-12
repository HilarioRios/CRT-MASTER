# Plugins

## Habilitados

| plugin | marketplace | scope | qué hace | por qué está activo |
|---|---|---|---|---|
| `superpowers` | `superpowers-marketplace` (github `obra/superpowers-marketplace`) | user | Suite completa de proceso (brainstorming, planning, TDD, debugging, review, etc.) | Ya estaba instalado y es la columna vertebral del workflow |
| `codex` | `openai-codex` (github `openai/codex-plugin-cc`) | user | Puente hacia Codex CLI para tareas delegadas | Ya estaba instalado |
| `the-architect` | `soyenriquerocha` (github `Hainrixz/the-architect`) | user | Meta-agente de arquitectura/blueprints | Ya estaba instalado |
| `hookify` | `claude-plugins-official` (oficial Anthropic) | user | Motor de reglas para guardrails de proyecto (ver `HOOKS.md`) | **Habilitado en esta sesión** — mecanismo oficial para los guardrails de `HILARIO-STARTER` |
| `context7` | `claude-plugins-official` | user | MCP de documentación de librerías (ver `MCPS.md`) | **Habilitado en esta sesión** — llena un hueco sin pedir credenciales |
| `claude-code-setup` | `claude-plugins-official` (oficial Anthropic) | user | Analiza un proyecto y recomienda hooks/skills/MCPs/subagentes/comandos a medida. Solo lectura, no modifica nada | **Habilitado en esta sesión**, permanente (no solo para esta auditoría) — es el mecanismo oficial que responde directamente al "skill discovery" que pediste. Costo real medido: `claude plugin details claude-code-setup@claude-plugins-official` reporta `~141 tok` siempre-activos por sesión (comparar: `hookify` ~294, `context7` ~0) — marginal, y justifica quedar prendido porque su valor (recomendaciones al arrancar cualquier proyecto nuevo) es recurrente, no un chequeo de una sola vez |

## Disponibles en `claude-plugins-official`, no habilitados (LIBRARY)

El marketplace ya estaba agregado (`extraKnownMarketplaces`) antes de esta sesión. Se revisaron todos sus plugins; quedan disponibles bajo demanda vía `claude plugin enable <nombre>@claude-plugins-official`:

| plugin | motivo para no activarlo por defecto |
|---|---|
| `github` | necesita `GITHUB_PERSONAL_ACCESS_TOKEN` — ver `MCPS.md` |
| `security-guidance` | hace llamadas a un `review_api`/LLM por diff (costo/latencia no determinística); se solapa con `cyber-neo` + la skill core `security-review` ya activa |
| `code-review` | duplica la skill core `code-review` ya activa por defecto en Claude Code |
| `skill-creator` (del marketplace) | duplica la skill core `skill-creator` / `anthropic-skills:skill-creator` ya disponible |
| `pr-review-toolkit`, `commit-commands`, `claude-md-management`, `session-report`, `feature-dev`, `project-artifact`, `code-modernization`, `agent-sdk-dev`, `mcp-server-dev`, `mcp-tunnels`, `ralph-loop` | utilidades de nicho — activarlas cuando un proyecto puntual lo justifique, no por defecto |
| LSPs (`kotlin-lsp`, `gopls-lsp`, `typescript-lsp`, `php-lsp`, `jdtls-lsp`, `rust-analyzer-lsp`, `swift-lsp`, `csharp-lsp`, `clangd-lsp`, `ruby-lsp`, `lua-lsp`, `pyright-lsp`) | activar solo el LSP del lenguaje que el proyecto en curso realmente usa |
| `playground`, `example-plugin`, `math-olympiad`, `learning-output-style`, `explanatory-output-style`, `receipts` | plugins de demo/nicho, sin uso claro para este sistema |

`external_plugins` relevantes ya cubiertos arriba (`github`, `context7`); el resto (`terraform`, `discord`, `gitlab`, `linear`, `serena`, `firebase`, `telegram`, `laravel-boost`, `imessage`, `asana`) quedan como LIBRARY — se activan solo si un proyecto concreto integra esa herramienta.

## Descartados

Ninguno de los evaluados se consideró inseguro o mal mantenido — todos son del marketplace oficial de Anthropic. "Descartado" acá significa "no core, no se activa por defecto", no "inseguro".
