# Cómo actualizar este sistema

## Marketplaces y plugins

```bash
claude plugin details <nombre>@<marketplace>   # ver estado/versión de un plugin puntual
claude plugin enable <nombre>@<marketplace>    # activar uno disponible (ver PLUGINS.md → LIBRARY)
claude plugin disable <nombre>@<marketplace>   # desactivar
```

Los marketplaces ya conocidos (`superpowers-marketplace`, `claude-plugins-official`, `openai-codex`, `soyenriquerocha`) se actualizan solos según la configuración de cada uno (`autoUpdate` en `extraKnownMarketplaces`, si está seteado) o manualmente re-agregando el marketplace.

## Re-auditar tododeia.com/community

Repetir el research (delegado a un agente en background, no en el hilo principal — ver `docs/superpowers/plans/2026-09-30-hilario-ai-dev-system.md`, Tarea 6) cada tanto, cruzando contra `INSTALLED.md` para detectar duplicados antes de instalar nada nuevo. No instalar nada sin verificar contra el repositorio/fuente oficial del recurso.

## Sincronizar cambios de `HILARIO-STARTER` a proyectos ya clonados

`HILARIO-STARTER` es una **plantilla**, no un paquete con sync en vivo. Si se actualizan sus reglas o `AGENTS.md`/`CLAUDE.md`, los proyectos que ya lo copiaron NO se actualizan solos. Para propagar un cambio:

1. Actualizar los archivos dentro de `HILARIO-STARTER/` en este repo.
2. Copiar manualmente los archivos cambiados al proyecto destino (o volver a correr `install.sh`, que sobrescribe `AGENTS.md`/`CLAUDE.md`/`.claude/rules/*`/`.claude/hookify.*.local.md` — cuidado si el proyecto ya personalizó alguno de esos archivos, revisar el diff antes).

## Hook global

Si hace falta bloquear un patrón nuevo, editar `~/.claude/hooks/guard-dangerous-bash.sh` directamente y volver a correr una batería de pruebas equivalente a la descrita en `HOOKS.md` antes de confiar en el cambio. No hace falta reiniciar Claude Code — el hook se re-lee en cada invocación de Bash.

## Revisar este inventario

`INSTALLED.md` tiene fecha de revisión por fila. Cuando se instale/desinstale algo, actualizar la fila correspondiente (o agregar una nueva) con la fecha del día.
