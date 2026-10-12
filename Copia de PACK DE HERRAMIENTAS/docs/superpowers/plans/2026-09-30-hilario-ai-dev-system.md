# HILARIO AI DEV SYSTEM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the GLOBAL Claude Code install (`~/.claude`) with real hook guardrails and credential-free MCPs, and build a portable `HILARIO-STARTER/` project template plus `docs/AI-SYSTEM/` documentation inside `/Users/hilario/Downloads/Claude/Replica`, without breaking or duplicating anything already installed.

**Architecture:** Two-layer hooks (hand-written global hard guard + official `hookify` plugin for project-visible rules), config changes via the `update-config` skill where it applies, MCP additions via the `claude` CLI, documentation as a fixed set of Markdown files under `docs/AI-SYSTEM/`.

**Tech Stack:** bash, jq, Claude Code hooks (`settings.json`), Claude Code plugins/MCP (`claude` CLI 2.1.285), Markdown.

---

## Task 1: Global guard hook — write + test the script

**Files:**
- Create: `/Users/hilario/.claude/hooks/guard-dangerous-bash.sh`
- Test: `/Users/hilario/Downloads/Claude/Replica/docs/superpowers/plans/tests/test-guard-hook.sh` (throwaway test harness, run once, not shipped)

- [x] **Step 1: Write the test harness first**

Create `docs/superpowers/plans/tests/test-guard-hook.sh`:

```bash
#!/usr/bin/env bash
set -uo pipefail
HOOK="$HOME/.claude/hooks/guard-dangerous-bash.sh"
pass=0; fail=0

check() {
  local desc="$1" cmd="$2" want_deny="$3"
  local out
  out=$(printf '{"tool_name":"Bash","tool_input":{"command":%s}}' "$(printf '%s' "$cmd" | jq -Rs .)" | "$HOOK")
  local decision
  decision=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [ "$want_deny" = "deny" ] && [ "$decision" = "deny" ]; then
    echo "PASS (blocked as expected): $desc"; pass=$((pass+1))
  elif [ "$want_deny" = "allow" ] && [ "$decision" != "deny" ]; then
    echo "PASS (allowed as expected): $desc"; pass=$((pass+1))
  else
    echo "FAIL: $desc -> got decision='$decision'"; fail=$((fail+1))
  fi
}

check "rm -rf on root-ish path"        'rm -rf /'                                  deny
check "rm -rf on home"                 'rm -rf ~'                                  deny
check "rm -rf wildcard from root"      'rm -rf /*'                                 deny
check "rm -rf node_modules (safe)"     'rm -rf node_modules'                       allow
check "rm -rf ./dist (safe)"           'rm -rf ./dist'                             allow
check "git push --force"               'git push --force origin main'             deny
check "git push --force-with-lease"    'git push --force-with-lease'               deny
check "normal git push"                'git push origin main'                     allow
check "git reset --hard"               'git reset --hard HEAD~3'                  deny
check "git reset soft (safe)"          'git reset --soft HEAD~1'                   allow
check "git clean -fd"                  'git clean -fd'                            deny
check "DROP DATABASE"                  'psql -c "DROP DATABASE prod;"'            deny
check "DROP TABLE"                     'mysql -e "DROP TABLE users;"'              deny
check "select is safe"                 'psql -c "SELECT * FROM users;"'           allow
check "overwrite .env"                 'echo foo > .env'                          deny
check "overwrite .env.production"      'printf "x" > .env.production'             deny
check "append safe to .env.example"    'echo foo >> .env.example'                 allow
check "rm single .env"                 'rm .env'                                  deny
check "git add .env"                   'git add .env'                             deny
check "git commit staged .env"         'git commit -am "oops with .env inside"'   allow
check "unrelated ls"                   'ls -la'                                   allow

echo "---"
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
```

- [x] **Step 2: Run it to confirm it fails (hook doesn't exist yet)**

Run: `chmod +x docs/superpowers/plans/tests/test-guard-hook.sh && bash docs/superpowers/plans/tests/test-guard-hook.sh`
Expected: every check fails or errors because `~/.claude/hooks/guard-dangerous-bash.sh` doesn't exist yet (`jq` parse error / decision empty / "allow" everywhere since the hook can't run).

- [x] **Step 3: Write the hook script**

Create `/Users/hilario/.claude/hooks/guard-dangerous-bash.sh`:

```bash
#!/usr/bin/env bash
# Global PreToolUse guard for the Bash tool.
# Hard-blocks a short, deliberately narrow list of irreversible/destructive
# command patterns. Everything else is allowed. See docs/AI-SYSTEM/HOOKS.md
# in the HILARIO-STARTER repo for the rationale and how to extend this list.
set -uo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

allow() {
  printf '{}'
  exit 0
}

[ -z "$command" ] && allow

# rm -rf / rm -fr on a broad or root-ish target: /, ~, $HOME, a bare wildcard,
# or a path that is just "/" with trailing segments like /* or /..
if printf '%s' "$command" | grep -qiE '\brm\b.*-[a-z]*r[a-z]*f[a-z]*\b|\brm\b.*-[a-z]*f[a-z]*r[a-z]*\b'; then
  if printf '%s' "$command" | grep -qE '(^|[[:space:]])(/|~|\$HOME)([[:space:]]|/\*?[[:space:]]*$|$)'; then
    deny "rm -rf sobre una ruta amplia o raíz ('/'," ~"," "\$HOME). Si es intencional, corré el comando manualmente fuera de Claude Code."
  fi
fi

# git push --force / --force-with-lease (any target)
if printf '%s' "$command" | grep -qE '\bgit\b.*\bpush\b.*(--force\b|--force-with-lease\b|-f\b)'; then
  deny "git push --force puede sobrescribir historia remota compartida. Hacelo manualmente si estás seguro."
fi

# git reset --hard
if printf '%s' "$command" | grep -qE '\bgit\b.*\breset\b.*--hard\b'; then
  deny "git reset --hard descarta cambios locales sin posibilidad de recuperarlos vía git. Hacelo manualmente si estás seguro."
fi

# git clean -fd (and variants like -fdx, -df)
if printf '%s' "$command" | grep -qE '\bgit\b.*\bclean\b.*-[a-z]*f[a-z]*d[a-z]*\b|\bgit\b.*\bclean\b.*-[a-z]*d[a-z]*f[a-z]*\b'; then
  deny "git clean -fd borra archivos no versionados de forma irreversible. Hacelo manualmente si estás seguro."
fi

# DROP DATABASE / DROP TABLE (any SQL client)
if printf '%s' "$command" | grep -qiE '\bdrop[[:space:]]+(database|table)\b'; then
  deny "DROP DATABASE/TABLE es destructivo e irreversible. Hacelo manualmente si estás seguro."
fi

# Known destructive migration rollback/reset commands
if printf '%s' "$command" | grep -qiE 'prisma[[:space:]]+migrate[[:space:]]+reset|rails[[:space:]]+db:drop|knex[[:space:]]+migrate:rollback[[:space:]]+--all|alembic[[:space:]]+downgrade[[:space:]]+base'; then
  deny "Comando de migración destructivo (reset/rollback total/downgrade a base). Hacelo manualmente si estás seguro."
fi

# Overwrite-redirect onto a real .env file (not .env.example/.env.sample/.env.template)
if printf '%s' "$command" | grep -qE '>[[:space:]]*\.env(\.[A-Za-z0-9_-]+)?([[:space:]]|$)'; then
  if ! printf '%s' "$command" | grep -qE '\.env\.(example|sample|template)\b'; then
    deny "Sobrescribe un archivo .env real. Editalo manualmente si es intencional."
  fi
fi

# rm on a real .env file
if printf '%s' "$command" | grep -qE '\brm\b.*[[:space:]]\.env(\.[A-Za-z0-9_-]+)?([[:space:]]|$)'; then
  if ! printf '%s' "$command" | grep -qE '\.env\.(example|sample|template)\b'; then
    deny "Borra un archivo .env real. Hacelo manualmente si es intencional."
  fi
fi

# git add / git commit of a real .env file
if printf '%s' "$command" | grep -qE '\bgit\b.*\badd\b.*[[:space:]]\.env(\.[A-Za-z0-9_-]+)?([[:space:]]|$)'; then
  if ! printf '%s' "$command" | grep -qE '\.env\.(example|sample|template)\b'; then
    deny "Agrega un archivo .env real al stage de git (riesgo de commitear secretos). Hacelo manualmente si es intencional."
  fi
fi

allow
```

- [x] **Step 4: Make it executable and run the test again**

Run: `chmod +x ~/.claude/hooks/guard-dangerous-bash.sh && bash docs/superpowers/plans/tests/test-guard-hook.sh`
Expected: `passed=20 failed=0` (all checks pass — every "deny" case is blocked, every "allow" case passes through).

If any check fails, fix the specific regex in the script (don't loosen a deny into an allow just to make the test pass — tighten the pattern instead) and re-run until `failed=0`.

- [x] **Step 5: Delete the throwaway test directory**

Run: `rm -rf docs/superpowers/plans/tests`

(The hook script itself lives in `~/.claude/hooks/`, outside this repo, since it's a GLOBAL machine guard. It gets documented, not committed, in this repo — see Task 6.)

---

## Task 2: Register the global hook + enable `hookify` and `context7`

**Files:**
- Modify: `/Users/hilario/.claude/settings.json`

- [x] **Step 1: Use the `update-config` skill to add the hooks block**

Invoke the `update-config` skill to add this to `~/.claude/settings.json` (merge into existing JSON, don't hand-edit blindly — validate the file parses with `jq . ~/.claude/settings.json` before and after):

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        { "type": "command", "command": "\"$HOME/.claude/hooks/guard-dangerous-bash.sh\"" }
      ]
    }
  ]
}
```

- [x] **Step 2: Verify the JSON is still valid**

Run: `jq . ~/.claude/settings.json > /dev/null && echo OK`
Expected: `OK`

- [x] **Step 3: Enable `hookify` and `context7` plugins**

Run:
```bash
claude plugin enable hookify@claude-plugins-official
claude plugin enable context7@claude-plugins-official
```
Expected: both report enabled (or already-enabled). Do NOT run `claude plugin enable github@claude-plugins-official` yet — that one needs `GITHUB_PERSONAL_ACCESS_TOKEN` (Task 5 documents it as a manual step).

- [x] **Step 4: Sanity-check the live hook end-to-end**

In a fresh throwaway directory (e.g. `/tmp`), ask Claude Code (this session) to run a harmless dangerous-looking command, e.g. `git reset --hard HEAD` inside a scratch git repo, and confirm the tool call is denied with the hook's message. (Manual verification step — record the result in the final report, don't just assert it works.)

- [x] **Step 5: Commit note in this repo (the settings.json itself isn't in this repo — nothing to commit here)**

No commit needed for this task (global file is outside the repo). Proceed to Task 3.

---

## Task 3: Add credential-free MCPs globally

**Files:**
- Modify: `/Users/hilario/.claude.json` (via `claude mcp add`, not hand-edited)

- [x] **Step 1: Add chrome-devtools MCP (user/global scope)**

Run: `claude mcp add chrome-devtools --scope user -- npx chrome-devtools-mcp@latest`
Expected: confirmation the server was added.

- [x] **Step 2: Verify it lists correctly**

Run: `claude mcp list`
Expected: output includes both `playwright` (already existing) and `chrome-devtools`.

- [x] **Step 3: Confirm context7 is reachable (no key needed)**

Since `context7` was enabled as a plugin in Task 2, verify via `claude mcp list` or `/mcp` inside a session that it shows up; note in the final report whether it connects without a key (expected: yes, rate-limited).

---

## Task 4: `HILARIO-STARTER/` — the portable project template

**Files:**
- Create: `HILARIO-STARTER/README.md`
- Create: `HILARIO-STARTER/install.sh`
- Create: `HILARIO-STARTER/AGENTS.md`
- Create: `HILARIO-STARTER/CLAUDE.md`
- Create: `HILARIO-STARTER/.claude/rules/security.md`
- Create: `HILARIO-STARTER/.claude/rules/working-contract.md`
- Create: `HILARIO-STARTER/.claude/rules/web-defaults.md`
- Create: `HILARIO-STARTER/.claude/hookify.block-dangerous-rm.local.md`
- Create: `HILARIO-STARTER/.claude/hookify.block-force-push.local.md`
- Create: `HILARIO-STARTER/.claude/hookify.block-reset-hard.local.md`
- Create: `HILARIO-STARTER/.claude/hookify.block-drop-database.local.md`
- Create: `HILARIO-STARTER/.claude/hookify.warn-env-files.local.md`
- Create: `HILARIO-STARTER/.claude/agents/README.md`
- Create: `HILARIO-STARTER/.claude/skills/README.md`

- [x] **Step 1: Create the 5 `hookify.*.local.md` rule files**

`HILARIO-STARTER/.claude/hookify.block-dangerous-rm.local.md`:
```markdown
---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|~|\$HOME)(\s|/\*?\s*$|$)
action: block
---

⚠️ **rm -rf sobre una ruta amplia o raíz.**

Si es intencional, corré el comando manualmente fuera de Claude Code.
```

`HILARIO-STARTER/.claude/hookify.block-force-push.local.md`:
```markdown
---
name: block-force-push
enabled: true
event: bash
pattern: git\s+push\s+.*(--force\b|--force-with-lease\b|-f\b)
action: block
---

⚠️ **git push --force detectado.**

Puede sobrescribir historia remota compartida. Hacelo manualmente si estás seguro.
```

`HILARIO-STARTER/.claude/hookify.block-reset-hard.local.md`:
```markdown
---
name: block-reset-hard
enabled: true
event: bash
pattern: git\s+reset\s+.*--hard\b
action: block
---

⚠️ **git reset --hard detectado.**

Descarta cambios locales sin posibilidad de recuperarlos vía git. Hacelo manualmente si estás seguro.
```

`HILARIO-STARTER/.claude/hookify.block-drop-database.local.md`:
```markdown
---
name: block-drop-database
enabled: true
event: bash
pattern: (?i)drop\s+(database|table)\b
action: block
---

⚠️ **DROP DATABASE/TABLE detectado.**

Operación destructiva e irreversible. Hacelo manualmente si estás seguro.
```

`HILARIO-STARTER/.claude/hookify.warn-env-files.local.md`:
```markdown
---
name: warn-env-files
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.env$|\.env\.[A-Za-z0-9_-]+$
---

🔐 **Estás editando un archivo .env.**

Confirmá que no estás commiteando secretos y que el archivo está en `.gitignore`.
```

- [x] **Step 2: Create the rules files**

`HILARIO-STARTER/.claude/rules/security.md`:
```markdown
# Seguridad

- No expongas ni imprimas contenido de `.env`, credenciales, tokens, API keys o llaves SSH en la conversación.
- No conectes cuentas externas, hagas deploy a producción, gastes dinero o publiques anuncios sin confirmación explícita del usuario.
- Antes de instalar una dependencia, skill o plugin de terceros, revisá su fuente/repositorio, mantenimiento y permisos.
- Ante cualquier comando irreversible (force push, reset --hard, DROP DATABASE, borrado masivo), confirmá con el usuario incluso si el hook global ya lo bloqueó — no busques un rodeo para saltarlo.
```

`HILARIO-STARTER/.claude/rules/working-contract.md`:
```markdown
# Contrato de trabajo

- Ejecutar de punta a punta cuando sea razonable; informar brevemente durante trabajos largos.
- No revertir cambios del usuario sin permiso explícito.
- No instalar dependencias, borrar archivos ni hacer cambios destructivos sin necesidad clara.
- Antes de afirmar que algo está terminado, verificarlo (build/typecheck/lint/tests/uso real) — no inventar verificaciones.
- Antes de finalizar, indicar qué se cambió y cómo se verificó.
```

`HILARIO-STARTER/.claude/rules/web-defaults.md`:
```markdown
---
paths:
  - "src/**/*.tsx"
  - "src/**/*.jsx"
  - "src/**/*.css"
  - "app/**/*.tsx"
  - "components/**/*.tsx"
---

# Reglas para proyectos web

- Construir la experiencia usable real primero, no una landing genérica.
- Layout responsive, jerarquía visual clara, estados completos (loading/error/empty).
- Usar convenciones de diseño ya existentes en el proyecto antes de inventar nuevas.
- Verificar visualmente en el navegador cuando sea posible antes de dar por terminado.
```

- [x] **Step 3: Create `.claude/agents/README.md` and `.claude/skills/README.md`**

`HILARIO-STARTER/.claude/agents/README.md`:
```markdown
# Agentes de proyecto

Los ~230 agentes especialistas ya están disponibles globalmente (`~/.claude/agents/`) — no se duplican acá.

Agregá un archivo `.md` en esta carpeta solo si este proyecto puntual necesita un agente con contexto/herramientas específicas del repo que no tenga sentido en ningún otro proyecto. Ver `docs/AI-SYSTEM/AGENTS.md` en el repo meta para el roster completo y el subconjunto CORE recomendado.
```

`HILARIO-STARTER/.claude/skills/README.md`:
```markdown
# Skills de proyecto

Las skills globales (`prompt-master`, `skill-router`, Superpowers, `the-architect`, `cyber-neo`, `all-deploy`, `claude-seo-ai`, `claude-ads`, la librería de marketing, etc.) ya están disponibles — no se duplican acá.

Agregá una carpeta `<nombre>/SKILL.md` acá solo para workflows específicos de este proyecto que no tengan sentido en otro repo. Ver `docs/AI-SYSTEM/SKILLS.md` en el repo meta para el catálogo completo.
```

- [x] **Step 4: Create `AGENTS.md` and `CLAUDE.md` (slim, routing/security/workflow only)**

`HILARIO-STARTER/AGENTS.md`:
```markdown
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

## Definición de terminado

No afirmar que algo está terminado solo porque se escribió código. Verificar con evidencia real (build/typecheck/lint/tests/uso en navegador/etc.) según corresponda a la tarea. Documentar qué se verificó.

## Referencias

Inventario completo, routing detallado y seguridad ampliada: `docs/AI-SYSTEM/` en el repo meta (`HILARIO AI DEV SYSTEM`) del que salió esta plantilla.
```

`HILARIO-STARTER/CLAUDE.md`:
```markdown
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
```

- [x] **Step 5: Create `install.sh` and `README.md`**

`HILARIO-STARTER/install.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-}"
if [ -z "$TARGET_DIR" ]; then
  echo "Uso: ./install.sh /ruta/al/proyecto/nuevo"
  exit 1
fi
if [ ! -d "$TARGET_DIR" ]; then
  echo "La carpeta no existe: $TARGET_DIR"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/AGENTS.md" "$TARGET_DIR/AGENTS.md"
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
mkdir -p "$TARGET_DIR/.claude/rules" "$TARGET_DIR/.claude/agents" "$TARGET_DIR/.claude/skills"
cp "$SCRIPT_DIR/.claude/rules/"*.md "$TARGET_DIR/.claude/rules/"
cp "$SCRIPT_DIR/.claude/hookify."*.local.md "$TARGET_DIR/.claude/"
cp "$SCRIPT_DIR/.claude/agents/README.md" "$TARGET_DIR/.claude/agents/README.md"
cp "$SCRIPT_DIR/.claude/skills/README.md" "$TARGET_DIR/.claude/skills/README.md"

echo "HILARIO-STARTER instalado en: $TARGET_DIR"
echo "- AGENTS.md, CLAUDE.md"
echo "- .claude/rules/*.md"
echo "- .claude/hookify.*.local.md (necesita el plugin 'hookify' habilitado globalmente)"
echo "- .claude/agents/README.md, .claude/skills/README.md"
echo "Completá el bloque 'Contexto del proyecto' en CLAUDE.md."
```

`HILARIO-STARTER/README.md`: explain what the folder is (the portable "mochila"), how to run `install.sh`, and that the hook rules only take effect if `hookify` is enabled globally (it is, after Task 2) — one short paragraph each, no filler.

- [x] **Step 6: Make install.sh executable and smoke-test it**

Run:
```bash
chmod +x HILARIO-STARTER/install.sh
mkdir -p /tmp/starter-smoke-test
./HILARIO-STARTER/install.sh /tmp/starter-smoke-test
find /tmp/starter-smoke-test -type f | sort
rm -rf /tmp/starter-smoke-test
```
Expected: the file list shows `AGENTS.md`, `CLAUDE.md`, `.claude/rules/security.md`, `.claude/rules/working-contract.md`, `.claude/rules/web-defaults.md`, 5 `.claude/hookify.*.local.md` files, `.claude/agents/README.md`, `.claude/skills/README.md`.

- [x] **Step 7: Commit**

```bash
git add HILARIO-STARTER/
git commit -m "feat: add portable HILARIO-STARTER project template"
```

---

## Task 5: `docs/AI-SYSTEM/` — system documentation

**Files:**
- Create: `docs/AI-SYSTEM/README.md`
- Create: `docs/AI-SYSTEM/INSTALLED.md`
- Create: `docs/AI-SYSTEM/SKILLS.md`
- Create: `docs/AI-SYSTEM/AGENTS.md`
- Create: `docs/AI-SYSTEM/PLUGINS.md`
- Create: `docs/AI-SYSTEM/MCPS.md`
- Create: `docs/AI-SYSTEM/HOOKS.md`
- Create: `docs/AI-SYSTEM/ROUTING.md`
- Create: `docs/AI-SYSTEM/SECURITY.md`
- Create: `docs/AI-SYSTEM/UPDATING.md`
- Create: `docs/AI-SYSTEM/TROUBLESHOOTING.md`
- Modify: `/Users/hilario/Downloads/Claude/Replica/README.md` (create if missing)

- [x] **Step 1: `INSTALLED.md`** — one table, columns exactly: `nombre | tipo | fuente | url | scope | categoría | estado | modo | qué hace | cuándo usarlo | qué lo activa | dependencias | conflictos | razón | fecha revisión`. Populate one row per: prompt-master, skill-router, every Superpowers skill, the-architect (+ subagents), cyber-neo, all-deploy, claude-seo-ai (+ subskills), claude-ads (+ subskills), the ~65 marketing skills (can group as one row "marketing skill library" with a sub-list, plus call out ab-test-setup/copywriting/seo-audit by name since they're highest-traffic), the core product skills (code-review, security-review, update-config, workflow-authoring, skill-creator, dataviz, artifact-design, etc.), the ~230 agents (one summary row + pointer to `AGENTS.md`), Playwright MCP, chrome-devtools MCP (new), context7 MCP (new), hookify plugin (new), github plugin (documented, not enabled), the global guard hook (new), and every `claude-plugins-official` plugin left un-enabled (LSPs, pr-review-toolkit, commit-commands, ralph-loop, security-guidance, etc. — grouped, status `available/library`). Date all rows `2026-09-30`.

- [x] **Step 2: `HOOKS.md`** — document both layers exactly (paste the final regex list from Task 1's script and the 5 hookify rule files from Task 4), explain why two layers, how to add a new rule (edit the global script for machine-wide, or add a `.claude/hookify.*.local.md` for project-only), and the explicit "no bloquea rm -rf node_modules, dist, build, etc." false-positive note.

- [x] **Step 3: `MCPS.md`** — table of `playwright` (existing), `chrome-devtools` (new, no creds), `context7` (new, no creds required, optional `CONTEXT7_API_KEY` for higher limits), `github` (documented, needs `GITHUB_PERSONAL_ACCESS_TOKEN`, exact command to run when the user decides to connect it — reuse `gh auth token` only if the user explicitly runs it themselves), and the still-connector-pending marketing MCPs (ahrefs, amplitude, canva, figma, klaviyo, notion, similarweb, slack, supermetrics) marked `REQUIERE ACCIÓN DE HILARIO`.

- [x] **Step 4: `PLUGINS.md`** — table of the 3 currently-enabled plugins (superpowers, codex, the-architect) plus the newly-enabled (hookify, context7) plus every other plugin seen under `claude-plugins-official` marked `LIBRARY` (available, not enabled) with a one-line reason each (LSP for unused language, demo/example plugin, overlaps existing core skill, makes LLM calls per diff so not default-on, etc.).

- [x] **Step 5: `SKILLS.md` and `AGENTS.md`** — `SKILLS.md`: bucket the full skill list (from the session's available-skills listing) into CORE / STARTER / ON-DEMAND / LIBRARY with a one-line reason each. `AGENTS.md`: same buckets for the agent roster, explicitly naming the small CORE subset Claude should default to reaching for (e.g. architect ≈ `the-architect` skill, frontend/backend/database specialists, qa/e2e, security-reviewer ≈ `cyber-neo`/Security Architect, researcher ≈ general-purpose/Trend Researcher, code-reviewer ≈ Code Reviewer agent + `code-review` skill, debugger ≈ `systematic-debugging` skill) vs. the large on-demand specialist bank.

- [x] **Step 6: `ROUTING.md`** — the flow diagram in prose: request → prompt-master (silent) → skill-router → ≤2 domain skills → Superpowers phase skill → agent only if it adds isolation/expertise/parallelism → implementation → verification → docs. Include the exact phase-chain table from the user's original CLAUDE.md (already authoritative — restate it here so it's discoverable from this repo too, don't contradict it).

- [x] **Step 7: `SECURITY.md`** — restate the guard-hook rules, the "no instales a ciegas" checklist the user gave (repo/mantenedor/actividad/permisos/hooks/MCPs/filesystem/shell/llamadas externas/secretos), and the explicit list of things Claude must always confirm before doing (deploy, connect accounts, spend money, touch prod, modify security-sensitive code).

- [x] **Step 8: `UPDATING.md`** — how to refresh: `claude plugin` commands to check for marketplace updates, where to re-run the tododeia audit, how to re-sync `HILARIO-STARTER` changes into already-cloned projects (it's a template, not a live sync — document that explicitly).

- [x] **Step 9: `TROUBLESHOOTING.md`** — cover: hook not firing (check `jq . ~/.claude/settings.json`, check the script is executable), hookify rules not applying (remember they're loaded relative to cwd — only work if `.claude/hookify.*.local.md` exists in that exact project), MCP not connecting (`claude mcp list`, check Node/npx version), plugin not enabling (`claude plugin details <name>`).

- [x] **Step 10: `README.md` (both the `docs/AI-SYSTEM/README.md` index and the repo-root `README.md`)** — root README: what this repo is (HILARIO AI DEV SYSTEM), the GLOBAL vs HILARIO-STARTER split, link to `docs/AI-SYSTEM/`. `docs/AI-SYSTEM/README.md`: index linking the other 9 files with a one-line description each.

- [x] **Step 11: Commit**

```bash
git add README.md docs/AI-SYSTEM/
git commit -m "docs: add AI-SYSTEM documentation (installed, hooks, MCPs, routing, security)"
```

---

## Task 6: tododeia.com cross-reference + final classification

**Depends on:** the background research agent (`ab7803a0ed82b7666`) launched earlier in this session.

- [x] **Step 1: Collect the research agent's report** (via `SendMessage`/notification, already in flight, non-blocking — check when it lands)
- [x] **Step 2: For each genuinely new (non-duplicate) resource it found**, verify against the resource's own repo/site (not just the vault's description), per the user's explicit rule.
- [x] **Step 3: Classify each as CORE/STARTER/ON-DEMAND/LIBRARY/DESCARTADO** with a one-line reason; append new rows to `docs/AI-SYSTEM/INSTALLED.md` (and `PLUGINS.md`/`SKILLS.md`/`MCPS.md` as relevant).
- [x] **Step 4: Only auto-install items that are free/local/open-source/reversible/no-credentials** — anything else gets documented as `REQUIERE ACCIÓN DE HILARIO`, not installed.
- [x] **Step 5: Commit** any doc updates from this pass: `git add docs/AI-SYSTEM && git commit -m "docs: incorporate tododeia.com resource audit"`.

---

## Task 7: Final verification pass

- [x] **Step 1: JSON validity** — `jq . ~/.claude/settings.json > /dev/null && echo OK` and `jq . ~/.claude.json > /dev/null && echo OK`.
- [x] **Step 2: Hook executes** — re-run (or reuse) the check from Task 1 Step 4 / Task 2 Step 4.
- [x] **Step 3: MCPs listed** — `claude mcp list` shows `playwright`, `chrome-devtools`; `/mcp`-equivalent shows `context7` reachable.
- [x] **Step 4: Plugins enabled** — `claude plugin details hookify@claude-plugins-official` and `...context7@claude-plugins-official` both report enabled.
- [x] **Step 5: No dangling references** — `grep -rn "docs/AI-SYSTEM" HILARIO-STARTER/` and confirm every referenced doc file actually exists; `find docs/AI-SYSTEM -name '*.md'` matches the 11 files planned.
- [x] **Step 6: `install.sh` smoke test re-run** (Task 4 Step 6) one more time post-doc-changes.
- [x] **Step 7: `git status` clean** (nothing uncommitted except intentionally-ignored files) and `git log --oneline` shows the expected commit sequence.
- [x] **Step 8: Write the 20-point final report** to the user in the conversation (not a new file) per the original request's "RESULTADO FINAL" checklist.

---

## Self-review notes (writing-plans skill step)

- Spec coverage: all 5 phases from the design doc map to Tasks 1–7 above (hooks=1–2, starter=4, MCPs=3, tododeia=6, docs+verification=5+7). Global vs starter split preserved throughout.
- No placeholders: every file has literal content above, not "add appropriate X".
- Type/name consistency: hook script path (`~/.claude/hooks/guard-dangerous-bash.sh`) and its registration command in Task 2 match exactly; the 5 hookify filenames in Task 4 match the filenames listed in the design doc's folder tree.
- `github` MCP is consistently treated as "documented, not enabled" across Tasks 2, 3, 5, 7 — no contradiction.

## Post-implementation: code review findings and fixes (2026-09-30)

A code-reviewer subagent (per `superpowers:requesting-code-review`) independently re-tested the hook script rather than trusting the throwaway 21-case suite, and found two Critical bypasses using ordinary (non-adversarial) command forms:

1. `rm -rf "/"` (quoted), `rm -rf ~/` (trailing slash), and `sh -c "rm -rf /"` / `bash -c "..."` / `eval "..."` all slipped past the root/home guard.
2. The `.env` protections (overwrite, `rm`, `git add`) only matched a bare `.env`, not `./config/.env` or `/abs/path/.env`.

Both were fixed in `~/.claude/hooks/guard-dangerous-bash.sh` (quote-stripping preprocessing + broadened boundary regexes) and re-verified: a new permanent regression suite (`docs/AI-SYSTEM/hooks-regression-test.sh`, 36 cases — the original 21 plus 15 covering the bypass classes) passes 36/36, and a live re-check (`rm -rf "/"` through the real Bash tool) confirmed the fix end-to-end.

The same duplicated regex existed in `HILARIO-STARTER/.claude/hookify.block-force-push.local.md` (fixed) and `hookify.block-dangerous-rm.local.md` (attempted fix **denied by the platform's own auto-mode safety classifier** — unrelated to this system's hook, could not be worked around per the denial's explicit instructions, documented as a pending one-line manual fix in `docs/AI-SYSTEM/HOOKS.md` and `TROUBLESHOOTING.md`). This does not weaken the actual security posture: Layer 1 (the global hand-written hook) already covers these bypass classes in every project regardless of Layer 2's state.

Also addressed from the same review: `claude-code-setup`'s justification in `docs/AI-SYSTEM/PLUGINS.md` was circular (justified by the one-time audit that used it) — rewritten with its actual ongoing-use case and measured token cost. `rm -rf` and `.env` scope claims in `docs/AI-SYSTEM/HOOKS.md` were tightened to be precise about what is and isn't covered.

**Second round:** a fresh reviewer subagent independently re-verified the fixes above (re-reading the script and running its own additional cases, not just the committed suite) and confirmed both Criticals fixed, plus found one further Important-level gap: command substitution / backslash-escaping (backticks, `$(...)`, `\/`) could still reconstruct a root-delete path. Fixed by extending the same quote-stripping preprocessing to also strip backtick/backslash/parenthesis characters (deliberately not `$`, to keep `$HOME` detection intact). The regression suite grew to 40 cases (40/40 pass). An inherent, disclosed limitation remains: command substitution whose output isn't visible in the static command text (e.g. a dynamically-computed path) cannot be caught by a static regex guard — documented in `docs/AI-SYSTEM/HOOKS.md`. Second reviewer's final verdict: "Ready to merge: Yes."
