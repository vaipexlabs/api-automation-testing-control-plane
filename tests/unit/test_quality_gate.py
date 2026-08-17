import json
from pathlib import Path

from vaipex_api_automation.quality_gate import build_decision


def _write_evidence(root: Path, *, failures: int, coverage: float) -> None:
    (root / "policies").mkdir()
    (root / "reports").mkdir()
    (root / "policies/quality-gate.json").write_text(
        json.dumps(
            {
                "minimum_coverage_percent": 85,
                "maximum_failures": 0,
                "maximum_errors": 0,
                "decision_on_success": "PASS",
                "decision_on_failure": "HOLD",
            }
        )
    )
    (root / "reports/junit.xml").write_text(
        f'<testsuites><testsuite tests="4" failures="{failures}" errors="0" />'
        "</testsuites>"
    )
    (root / "reports/coverage.json").write_text(
        json.dumps({"totals": {"percent_covered": coverage}})
    )


def test_quality_gate_passes_compliant_evidence(tmp_path: Path) -> None:
    _write_evidence(tmp_path, failures=0, coverage=90)

    decision = build_decision(tmp_path)

    assert decision["decision"] == "PASS"
    assert decision["tests"] == 4


def test_quality_gate_holds_noncompliant_evidence(tmp_path: Path) -> None:
    _write_evidence(tmp_path, failures=1, coverage=70)

    decision = build_decision(tmp_path)

    assert decision["decision"] == "HOLD"
    assert len(decision["rationale"]) == 2
