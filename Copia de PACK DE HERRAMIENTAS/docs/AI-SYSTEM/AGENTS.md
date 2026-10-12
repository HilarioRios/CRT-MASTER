# Agentes — roster y subconjunto CORE

~230 agentes especialistas ya instalados en `~/.claude/agents/`. Claude Code principal actúa como **orquestador**: delega solo cuando un agente aporta aislamiento de contexto, expertise específico, investigación extensa, revisión independiente o paralelización real. Evitar delegaciones innecesarias en tareas chicas.

## Subconjunto CORE recomendado (los que el orquestador debería considerar primero)

| rol conceptual | agente(s) instalado(s) más cercano(s) |
|---|---|
| architect | `the-architect` (skill/plugin) + agente `Software Architect` / `Backend Architect` según el caso |
| product-reverse-engineer | `Codebase Onboarding Engineer`, `Explore` (búsqueda read-only), `general-purpose` para investigación amplia |
| frontend-engineer | `Frontend Developer`, `UI Designer`, `UX Architect` |
| backend-engineer | `Backend Architect`, `Database Optimizer`, `API Tester` |
| database-engineer | `Database Optimizer` |
| qa-e2e | `API Tester`, agente `Explore` + skill `agent-browser` / MCPs `playwright`/`chrome-devtools` |
| security-reviewer | skill `cyber-neo`, agentes `Security Architect`, `Application Security Engineer`, `Penetration Tester` (con autorización), `Senior SecOps Engineer` |
| researcher | `general-purpose`, `Trend Researcher`, `claude-code-guide` (para dudas sobre el propio Claude Code) |
| code-reviewer | skill core `code-review` + agente `Code Reviewer` |
| debugger | skill `superpowers:systematic-debugging` (proceso) — no hace falta un agente dedicado salvo que el bug requiera investigación aislada |

## Resto del roster (LIBRARY — bajo demanda)

Cubre prácticamente cualquier rol de negocio además de ingeniería: ventas (`Sales Engineer`, `Deal Strategist`, `Sales Coach`...), finanzas (`CFO`, `FP&A Analyst`, `Bookkeeper & Controller`...), legal (`Legal Document Review`, `Legal Compliance Checker`...), RRHH, producto, marketing (gran parte ya cubierta por las skills de marketing), soporte, gaming (Unity/Unreal/Godot/Roblox), geoespacial (GIS), y más de una docena de agentes para mercados de China (Douyin, Xiaohongshu, Weibo, etc.). No se listan uno por uno acá — usar el listado de agentes disponibles del `Agent` tool para buscar por nombre/descripción cuando haga falta un especialista puntual.

## Agentes ya usados como parte de este sistema

- `claude-code-guide` — se usó en esta sesión para confirmar la sintaxis actual de hooks/MCP/plugins antes de implementar nada (evitó inventar una estructura incompatible).
- `general-purpose` — se usó para el research en tododeia.com/community (ver `INSTALLED.md`/sección tododeia si aplica, y el hallazgo se integra al final de este documento cuando el agente responde).

## Regla de activación

1. Resolver primero con skills base.
2. Activar un agente solo si aporta algo que el hilo principal no puede hacer igual de bien (aislamiento, paralelismo, expertise).
3. No cargar varios agentes a la vez sin necesidad.
4. Para acciones de riesgo real (deploy, seguridad, cuentas externas, gasto), confirmar explícitamente antes de ejecutar, incluso si el agente lo recomienda.
