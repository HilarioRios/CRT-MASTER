# Routing

## Flujo conceptual

```
petición del usuario
  ↓
identificar intención
  ↓
prompt-master (silencioso, siempre)
  ↓
skill-router (elige ≤2 domain skills)
  ↓
skill(s) específica(s)
  ↓
agente especializado SOLO si aporta aislamiento/expertise/paralelismo
  ↓
ejecución
  ↓
testing / verificación
  ↓
documentación cuando corresponda
  ↓
terminado
```

## Cadenas obligatorias por intención (ya vigentes en `~/.claude/CLAUDE.md`, restated acá para que quede en este repo también)

| Intención | Cadena |
|---|---|
| Crear / modificar | `brainstorming` → `writing-plans` → `test-driven-development` → implementar → `verification-before-completion` → `requesting-code-review` (siempre, no solo en cambios grandes) |
| Bug / diagnóstico | `systematic-debugging` → (si el usuario autoriza el fix) `test-driven-development` → implementar → `verification-before-completion` → `requesting-code-review` |
| Prompt / instrucciones / delegación | `prompt-master` (silencioso salvo que se pida el prompt como artifact) |
| Petición de dominio | `prompt-master` → `skill-router` → máximo 2 domain skills |
| Review-only | Todo el flujo se queda en modo lectura — identificar un defecto no autoriza arreglarlo |
| Finalización de rama | `finishing-a-development-branch` |

## Reglas del router

- Elegir por el resultado principal pedido, no por palabras incidentales.
- Máximo 2 domain skills simultáneas, y solo si cubren partes distintas y necesarias.
- Cargar las process skills de Superpowers de forma secuencial, solo al empezar su fase — nunca precargar toda la cadena.
- No listar el inventario completo salvo que el usuario lo pida.
- Si ninguna domain/process skill aplica, seguir sin anuncio tras aplicar `prompt-master`/`skill-router` en silencio.

## Tamaño de la tarea

No forzar todas las etapas para tareas chicas. Una corrección de una línea no necesita brainstorming formal; un feature nuevo grande sí. El criterio: ¿una suposición razonable causaría retrabajo importante? Si no, seguir. Si sí, preguntar primero.
