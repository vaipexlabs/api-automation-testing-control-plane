#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Vaipex API Automation Testing Control Plane"
echo "============================================"
echo
echo "1/4 Validate the locked toolchain"
"${PROJECT_ROOT}/scripts/validate-toolchain.sh"
echo
echo "2/4 Enforce static quality controls"
"${PROJECT_ROOT}/.venv/bin/ruff" check src tests
echo
echo "3/4 Exercise every API quality layer and generate evidence"
"${PROJECT_ROOT}/scripts/quality-gate.sh"
echo
echo "4/4 Publish the release decision"
echo "Evidence: reports/api-automation.html"
echo "Decision: reports/quality-decision.json"
echo "PASS: the API satisfied the versioned Vaipex quality policy."
