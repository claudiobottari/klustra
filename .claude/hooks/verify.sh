#!/usr/bin/env bash
# Stop hook: enforces CLAUDE.md's "definition of done" mechanically.
# No-op until pyproject.toml exists. Once the project is scaffolded,
# a session cannot end silently on red tests/lint/types.
if [ ! -f pyproject.toml ]; then
  exit 0
fi

echo "--- ruff ---"
uv run ruff check . && uv run ruff format --check .
RUFF=$?

echo "--- mypy ---"
uv run mypy klustra/ 2>/dev/null
MYPY=$?

echo "--- pytest ---"
uv run pytest -q
PYTEST=$?

if [ $RUFF -ne 0 ] || [ $MYPY -ne 0 ] || [ $PYTEST -ne 0 ]; then
  echo "Verification failed (ruff=$RUFF mypy=$MYPY pytest=$PYTEST). Fix before stopping."
  exit 1
fi
exit 0
