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
