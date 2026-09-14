#!/usr/bin/env bash
# paper-research Skill Installer for Claude Code
# Creates a symlink in ~/.claude/skills/ pointing to the global skill dir.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SKILLS="${HOME}/.claude/skills"
LINK="${CLAUDE_SKILLS}/paper-research"

echo "=== paper-research installer ==="
echo "Source: ${SCRIPT_DIR}"
echo "Link  : ${LINK}"

mkdir -p "${CLAUDE_SKILLS}"

if [ -L "${LINK}" ] || [ -e "${LINK}" ]; then
    echo "  paper-research already exists at ${LINK}, removing to refresh..."
    rm -f "${LINK}"
fi

ln -s "${SCRIPT_DIR}" "${LINK}"
echo "  Created symlink: ${LINK}"

echo
echo "=== Done ==="
echo "Restart Claude Code (or /clear) for the new skill to take effect."
echo "Test: python ${SCRIPT_DIR}/scripts/paper_research.py --check-keys"
