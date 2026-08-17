#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Run ./scripts/setup.sh before validating the toolchain." >&2
  exit 1
fi

"${PYTHON}" - <<'PY'
from importlib.metadata import version
import sys

expected = {
    "fastapi": "0.141.1",
    "httpx": "0.28.1",
    "jsonschema": "4.26.0",
    "pydantic": "2.13.4",
    "pytest": "9.1.1",
    "pytest-asyncio": "1.4.0",
    "pytest-cov": "7.1.0",
    "pytest-html": "4.2.0",
    "pytest-xdist": "3.8.0",
    "respx": "0.23.1",
    "ruff": "0.16.3",
    "schemathesis": "4.24.3",
    "uvicorn": "0.52.3",
}

assert sys.version_info[:2] == (3, 12), sys.version
for distribution, required_version in expected.items():
    installed_version = version(distribution)
    assert installed_version == required_version, (
        f"{distribution}: expected {required_version}, found {installed_version}"
    )

print("Toolchain contract validated:")
print(f"  Python {sys.version.split()[0]}")
for distribution, required_version in expected.items():
    print(f"  {distribution} {required_version}")
PY

"${PYTHON}" -m pip check
