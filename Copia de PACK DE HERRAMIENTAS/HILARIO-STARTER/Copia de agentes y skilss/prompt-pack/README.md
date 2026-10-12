# Prompt Pack Reutilizable

Este paquete sirve para arrancar proyectos con la misma base de instrucciones: `prompt-master`, Superpowers, modo Arquitecto y reglas para peticiones de Codex, Claude Code, Cursor o chats con agentes.

## Que Incluye

- `AGENTS.base.md`: instrucciones base para Codex y agentes que leen `AGENTS.md`.
- `CLAUDE.base.md`: version equivalente para Claude Code.
- `project-instructions.md`: texto corto para pegar en instrucciones de proyecto de ChatGPT, Claude, Cursor, etc.
- `install.md`: guia para instalarlo en otros proyectos.

## Uso Rapido

1. Copiar `AGENTS.base.md` como `AGENTS.md` en la raiz del proyecto.
2. Si usas Claude Code, copiar `CLAUDE.base.md` como `CLAUDE.md`.
3. Si usas ChatGPT Projects, Claude Projects, Cursor o una herramienta similar, pegar `project-instructions.md` en las instrucciones del proyecto.
4. Ajustar el bloque "Contexto del proyecto" con el objetivo real de cada proyecto.

## Regla Principal

La capa base no reemplaza el pedido puntual del usuario: lo ordena. Si una instruccion global choca con una instruccion especifica del proyecto, gana la instruccion especifica del proyecto.
