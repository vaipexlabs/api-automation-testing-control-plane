#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"${PROJECT_ROOT}/scripts/ensure-toolchain.sh"
mkdir -p "${PROJECT_ROOT}/reports"

set +e
"${PROJECT_ROOT}/.venv/bin/pytest" \
  --cov=vaipex_api_automation \
  --cov-report=term-missing \
  --cov-report="json:${PROJECT_ROOT}/reports/coverage.json" \
  --junitxml="${PROJECT_ROOT}/reports/junit.xml" \
  --html="${PROJECT_ROOT}/reports/api-automation.html" \
  --self-contained-html
TEST_EXIT=$?
set -e

if [[ ! -f "${PROJECT_ROOT}/reports/junit.xml" || ! -f "${PROJECT_ROOT}/reports/coverage.json" ]]; then
  echo "HOLD: required test evidence was not generated."
  exit "${TEST_EXIT:-1}"
fi

set +e
"${PROJECT_ROOT}/.venv/bin/python" -m vaipex_api_automation.quality_gate
GATE_EXIT=$?
set -e
if [[ "${TEST_EXIT}" -ne 0 || "${GATE_EXIT}" -ne 0 ]]; then
  exit 1
fi
