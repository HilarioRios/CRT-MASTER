# Claude Code — instrucciones de proyecto

Ver también `AGENTS.md` (misma capa base, para Codex/otros agentes) y `.claude/rules/*.md`.

## Prioridad

1. Responder al pedido concreto del usuario.
2. Aplicar `prompt-master` como capa silenciosa de calidad.
3. Activar skills/modos opcionales solo cuando aporten valor real.
4. Mantener el trabajo acotado, verificable, sin cambios destructivos innecesarios (reforzado por hooks globales + `.claude/hookify.*.local.md`).

## Contexto del proyecto

- Nombre:
- Objetivo:
- Público:
- Stack preferido:
- Restricciones:
- Qué no debe tocarse:
- Criterios de terminado:

## Estilo de respuesta

- Hablar en español si el usuario escribe en español.
- Actualizaciones cortas y útiles durante trabajos largos.
- Resumir qué cambió y cómo se verificó al cerrar la tarea.
