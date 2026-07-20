#!/usr/bin/env bash
# PostToolUse hook: runs after every Edit/Write. No-op until pyproject.toml exists
# (i.e. before Fase 1 scaffold), so it's safe to install on day one.
set -e
if [ -f pyproject.toml ]; then
  uv run ruff check --fix . --quiet 2>/dev/null || true
  uv run ruff format --quiet . 2>/dev/null || true
fi
exit 0
