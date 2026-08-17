#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"${PROJECT_ROOT}/scripts/ensure-toolchain.sh"

"${PROJECT_ROOT}/.venv/bin/ruff" check src tests
"${PROJECT_ROOT}/.venv/bin/pytest" -q
