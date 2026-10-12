# Seguridad

## Guardrails activos

Ver `HOOKS.md` para el detalle técnico. Resumen: hook global (`~/.claude/hooks/guard-dangerous-bash.sh`) + reglas `hookify` en `HILARIO-STARTER/.claude/` bloquean `rm -rf` amplio, `git push --force`, `git reset --hard`, `git clean -fd`, `DROP DATABASE/TABLE`, migraciones destructivas conocidas, y sobrescritura/stage de `.env` real.

## Antes de instalar código o plugins de terceros (checklist aplicado en esta sesión)

- Repositorio y mantenedor: confirmados (todos los plugins nuevos son del marketplace oficial `claude-plugins-official`, publicados por Anthropic).
- Actividad/mantenimiento: `hookify` y `context7` tienen manifiestos claros y código legible; se leyó el código fuente completo de `hookify` (no solo la documentación) antes de habilitarlo, específicamente para confirmar que `action: block` bloquea de verdad y que no hace llamadas de red ni a un LLM.
- Permisos/acceso al filesystem/ejecución shell: `hookify` corre scripts Python locales (`pretooluse.py`, etc.) sin llamadas externas; `context7` y `chrome-devtools` son MCPs declarados explícitamente, sin scripts de instalación sospechosos.
- Llamadas externas: `context7` llama a `https://mcp.context7.com` (documentado, sin credenciales obligatorias); `chrome-devtools` corre 100% local sobre el Chrome DevTools Protocol.
- Secretos: ninguno de los tres requiere ni expone credenciales. `github` sí requiere un PAT — por eso quedó sin habilitar (ver `MCPS.md`).

## Reglas siempre vigentes

- No exponer `.env`, tokens, cookies, contraseñas, API keys ni llaves SSH.
- No conectar cuentas externas, hacer deploy a producción, gastar dinero ni publicar anuncios sin confirmación explícita.
- No tocar código de seguridad/autenticación/permisos sin confirmación.
- Ante un hallazgo de seguridad potencial de un plugin/skill de terceros: no instalarlo y documentar por qué (ver `PLUGINS.md` → sección "Descartados").
- Los hooks son el mecanismo preferido sobre instrucciones de texto para cualquier cosa que pueda protegerse técnicamente — no confiar solo en que el modelo "se acuerde" de no hacer algo destructivo.

## Qué NO se hizo (a propósito)

- No se generó ni usó ningún token/credencial nuevo.
- No se habilitó `github` pese a que `gh` ya está logueado — se documentó el comando exacto para cuando el usuario decida activarlo.
- No se conectaron los MCPs de marketing pendientes (ahrefs, figma, notion, slack, etc.).
- No se hizo push, deploy, ni ninguna acción hacia infraestructura compartida.
