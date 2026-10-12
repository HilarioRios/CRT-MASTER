#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-}"

if [ -z "$TARGET_DIR" ]; then
  echo "Uso: ./prompt-pack/install.sh /ruta/al/proyecto"
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "La carpeta no existe: $TARGET_DIR"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/AGENTS.base.md" "$TARGET_DIR/AGENTS.md"
cp "$SCRIPT_DIR/CLAUDE.base.md" "$TARGET_DIR/CLAUDE.md"
cp "$SCRIPT_DIR/optional-stack.md" "$TARGET_DIR/optional-stack.md"

echo "Prompt pack instalado en: $TARGET_DIR"
echo "- AGENTS.md"
echo "- CLAUDE.md"
echo "- optional-stack.md"
