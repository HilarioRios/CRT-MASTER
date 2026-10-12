# Troubleshooting

## El hook global no bloquea nada

1. `jq . ~/.claude/settings.json > /dev/null && echo OK` — si falla, el JSON está roto y **todo** `~/.claude/settings.json` queda inválido (no solo los hooks).
2. Confirmar que el script existe y es ejecutable: `test -x ~/.claude/hooks/guard-dangerous-bash.sh && echo OK`.
3. Probar el script directo, sin pasar por Claude Code: `echo '{"tool_name":"Bash","tool_input":{"command":"git reset --hard HEAD"}}' | ~/.claude/hooks/guard-dangerous-bash.sh` — debe imprimir un JSON con `"permissionDecision":"deny"`.
4. Si el script funciona solo pero Claude Code no lo aplica, revisar `jq -e '.hooks.PreToolUse[] | select(.matcher=="Bash")' ~/.claude/settings.json` — si no hay match, el bloque de hooks no quedó bien formado.

## Las reglas `hookify.*.local.md` de un proyecto no se aplican

Causa más común: el plugin `hookify` recarga sus reglas con un glob **relativo al directorio de trabajo actual** (`.claude/hookify.*.local.md`), no desde `~/`. Si Claude Code no está corriendo exactamente en la raíz de ese proyecto, o los archivos no están en `<proyecto>/.claude/`, no se cargan. Confirmar con `claude plugin details hookify@claude-plugins-official` que el plugin está habilitado, y que `ls .claude/hookify.*.local.md` desde la raíz del proyecto muestra los archivos.

## Un MCP nuevo no aparece en `claude mcp list` o `/mcp`

- Para un MCP registrado por `claude mcp add` (como `chrome-devtools`): correr `claude mcp list` de nuevo; si sigue sin aparecer, revisar `jq . ~/.claude.json` para confirmar que la entrada quedó bien escrita.
- Para un MCP que viene de un plugin recién habilitado (como `context7`): puede necesitar una sesión nueva de Claude Code para cargarse. No es necesariamente un error.
- `chrome-devtools` específicamente necesita Node ≥20.19 y Chrome estable instalados — confirmar con `node --version` y que Chrome abre normalmente.

## Un plugin no se deja habilitar

`claude plugin details <nombre>@<marketplace>` muestra el estado y el inventario de componentes. Si el marketplace no está en `extraKnownMarketplaces`, hay que agregarlo primero (no es el caso de `claude-plugins-official`, que ya estaba agregado).

## `install.sh` de HILARIO-STARTER falla

Confirmar que se está pasando una carpeta que ya existe como argumento (`./install.sh /ruta/existente`, no una ruta nueva) y que `install.sh` tiene permiso de ejecución (`chmod +x HILARIO-STARTER/install.sh`).

## Una edición a un archivo `hookify.*.local.md` es rechazada por "el clasificador de auto mode"

Le pasó a esta misma implementación: intentar editar `HILARIO-STARTER/.claude/hookify.block-dangerous-rm.local.md` para corregir su regex de `rm -rf` fue denegado por un clasificador de seguridad de la propia plataforma (no por el hook de este sistema), aparentemente por el contenido "rm -rf" del patrón. No hay forma de rodear esto desde la sesión — es una decisión de la plataforma, no de este repo. Si te pasa lo mismo: editá el archivo vos mismo (manualmente, fuera de la sesión de Claude Code), o pedile a Claude que te dé el diff exacto para aplicarlo vos. Ver `HOOKS.md` → "Gap conocido en la Capa 2" para el diff pendiente concreto.

## Referencias rotas en la documentación

Si un archivo de `docs/AI-SYSTEM/` menciona una skill/agente/plugin que ya no existe, es señal de que algo se desinstaló sin actualizar el inventario — corregir `INSTALLED.md` (y el archivo específico) en el mismo cambio que desinstala algo.
