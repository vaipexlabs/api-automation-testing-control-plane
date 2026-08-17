#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8080}"

"${PROJECT_ROOT}/scripts/ensure-toolchain.sh"
exec "${PROJECT_ROOT}/.venv/bin/uvicorn" \
  vaipex_api_automation.app:app \
  --host 127.0.0.1 \
  --port "${PORT}"
