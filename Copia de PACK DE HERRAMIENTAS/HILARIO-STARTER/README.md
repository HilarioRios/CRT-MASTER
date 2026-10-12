# HILARIO-STARTER

La "mochila" portable de Claude Code: se copia a cada proyecto nuevo para arrancar con routing, seguridad y reglas ya definidas, sin depender de configurar todo desde cero.

## Qué trae

- `AGENTS.md` / `CLAUDE.md`: capa base de routing, seguridad y workflow — chica a propósito, y autosuficiente (no depende de ningún otro archivo externo).
- `.claude/rules/`: reglas de seguridad, contrato de trabajo y defaults de proyectos web (convención oficial `.claude/rules/*.md`, algunas con `paths:` para cargar solo en archivos relevantes).
- `.claude/hookify.*.local.md`: guardrails de proyecto (rm -rf, force push, reset --hard, DROP DATABASE, aviso en `.env`) usando el plugin oficial `hookify`.
- `.claude/agents/README.md`, `.claude/skills/README.md`: punteros al roster global — no duplican los ~230 agentes ni las ~65+ skills que ya existen en `~/.claude`.

## Instalación

```bash
./install.sh /ruta/al/proyecto/nuevo
```

Copia los archivos de arriba al proyecto destino y te recuerda completar el bloque "Contexto del proyecto" en `CLAUDE.md`.

## Importante sobre los hooks de proyecto

Las reglas `.claude/hookify.*.local.md` solo se aplican si el plugin `hookify` está habilitado GLOBALMENTE (`~/.claude/settings.json` → `enabledPlugins`) — ya quedó habilitado. Además, hay un hook global hecho a mano (`~/.claude/hooks/guard-dangerous-bash.sh`) que protege cualquier proyecto, tenga o no estas reglas copiadas, bloqueando `rm -rf` amplio/raíz, `git push --force`, `git reset --hard`, `git clean -fd`, `DROP DATABASE/TABLE`, migraciones destructivas conocidas, y exposición de `.env` real.
