# AGENTS.md

## Capa global obligatoria

1. Para todo trabajo sustantivo: `prompt-master` (silencioso) → `skill-router` (elige hasta 2 domain skills).
2. Cadenas de Superpowers según intención:
   - Crear/modificar: `brainstorming` → `writing-plans` → `test-driven-development` → implementar → `verification-before-completion` → `requesting-code-review`.
   - Bug/diagnóstico: `systematic-debugging` → (si hay fix) `test-driven-development` → implementar → `verification-before-completion`.
   - Cierre de rama: `finishing-a-development-branch`.
3. Review-only: quedarse en modo lectura, sin escrituras ni commits implícitos.

## Seguridad

Ver `.claude/rules/security.md`. Los hooks de guardrail (rm -rf, force push, reset --hard, DROP DATABASE, .env) están activos GLOBALMENTE (`~/.claude/hooks/`) más las reglas de proyecto en `.claude/hookify.*.local.md` — no los desactives ni los rodees.

## Stack opcional (activar solo si la intención lo pide)

- `the-architect`: arquitectura, blueprints, decisiones técnicas grandes.
- `cyber-neo`: auditoría de seguridad y vulnerabilidades.
- `all-deploy`: correr local, preview, deploy (pedir confirmación antes de producción).
- `claude-seo-ai`: SEO técnico + visibilidad en buscadores IA.
- `claude-ads`: paid ads, Meta/Google/TikTok, presupuestos, creatividad.
- MCPs: `chrome-devtools` + `playwright` para browser automation / reverse engineering; `context7` para lookup de documentación de librerías.

## Al iniciar un proyecto nuevo: candidatos a evaluar (no instalados por defecto)

En la primera sesión de un proyecto nuevo (fase de arquitectura/setup, o cuando se use `claude-code-setup` para recomendar automatizaciones), evaluar también estos tres candidatos ya investigados — no asumir que no hacen falta solo porque no están instalados globalmente:

- **Claude Mem** (`thedotmack/claude-mem`, memoria persistente entre sesiones vía hooks+SQLite) — instalar si el proyecto es largo/complejo, se va a retomar en muchas sesiones separadas, y la memoria automática nativa de Claude Code no alcanza. No instalar junto con Context Mode sin probar antes (los dos tocan hooks de contexto).
- **Context Mode** (`mksglu/context-mode`, comprime el contexto de herramientas) — instalar si el proyecto genera mucho output de herramientas (logs largos, muchos archivos) y las sesiones se quedan sin contexto seguido.
- **Agency Agents** (`msitarzewski/agency-agents`, 144 agentes especialistas adicionales) — instalar solo si el proyecto necesita un rol de negocio que el roster actual (~230 agentes) no cubre bien, y solo después de comparar contra ese roster para no duplicar.

Si alguno aplica claramente (son gratuitos, locales, reversibles, sin credenciales), instalarlo directamente e informar al usuario qué se instaló y por qué al cerrar la tarea — no hace falta pedir permiso antes, ya quedó autorizado acá. Si no aplica ninguno, no instalar nada y seguir de largo.

## Definición de terminado

No afirmar que algo está terminado solo porque se escribió código. Verificar con evidencia real (build/typecheck/lint/tests/uso en navegador/etc.) según corresponda a la tarea. Documentar qué se verificó.

## Referencias

Este archivo es autosuficiente — no depende de ningún otro repo o carpeta externa. Para el roster completo de skills/agentes globales disponibles, preguntarle directamente a Claude ("qué skills tenés disponibles") en vez de buscar un inventario escrito aparte.
