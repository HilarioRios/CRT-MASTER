# MCPs

## Activos

| MCP | transporte | scope | credenciales | qué da |
|---|---|---|---|---|
| `playwright` | stdio (`npx @playwright/mcp@latest`) | global (`~/.claude.json`) | ninguna | Browser automation: navegar, click, formularios, screenshots, network/console inspection |
| `chrome-devtools` | stdio (`npx chrome-devtools-mcp@latest`) | global (`~/.claude.json`, agregado en esta sesión) | ninguna (requiere Chrome instalado y Node ≥20.19) | Chrome DevTools Protocol directo: consola, network, performance tracing, Lighthouse, DOM — complementa a Playwright para reverse engineering |
| `context7` | http (plugin `context7@claude-plugins-official`, agregado en esta sesión) | global | ninguna obligatoria (`CONTEXT7_API_KEY` opcional, sube el rate limit) | Documentación y ejemplos de código actualizados de librerías/frameworks directo al contexto |

`claude mcp list` puede tardar una sesión nueva en reflejar un MCP servido por un plugin recién habilitado (como `context7`) — si no aparece, no es un error, hace falta una sesión nueva o `/mcp` para forzar la carga.

## Documentados, pendientes de acción del usuario

| MCP | por qué no se activó | cómo activarlo cuando quieras |
|---|---|---|
| `github` (`github@claude-plugins-official`) | Requiere `GITHUB_PERSONAL_ACCESS_TOKEN` vía header `Authorization`. Aunque `gh` ya está logueado como `HilarioRios`, usar ese acceso para un MCP nuevo es "conectar una cuenta" y se pidió confirmación explícita antes de eso. | `claude plugin enable github@claude-plugins-official` y después exportar `GITHUB_PERSONAL_ACCESS_TOKEN` (por ejemplo, `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)` si querés reusar el token de `gh`, o generar un PAT de alcance acotado). |
| `ahrefs`, `amplitude`, `amplitude-eu`, `canva`, `figma`, `klaviyo`, `notion`, `similarweb`, `slack`, `supermetrics` (plugin `marketing`) | Necesitan OAuth/API key por plataforma. | Autorizar cada uno desde la configuración de conectores de claude.ai, o vía `claude mcp`/`/mcp` en una sesión interactiva. No se inventan credenciales. |

## Evaluados y descartados por ahora

Ninguno — los dos MCPs nuevos (`chrome-devtools`, `context7`) cubren los huecos identificados (Chrome DevTools, documentación de librerías) sin pedir credenciales. Si en el futuro hace falta un MCP de base de datos o filesystem específico de un proyecto, agregarlo ahí (scope `project`, `.mcp.json`), no acá.
