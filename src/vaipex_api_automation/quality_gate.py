"""Convert test and coverage evidence into one explainable quality decision."""

import json
from pathlib import Path
from xml.etree import ElementTree


def build_decision(project_root: Path) -> dict[str, object]:
    reports = project_root / "reports"
    policy = json.loads((project_root / "policies/quality-gate.json").read_text())
    suite = ElementTree.parse(reports / "junit.xml").getroot()
    coverage = json.loads((reports / "coverage.json").read_text())

    suites = [suite] if suite.tag == "testsuite" else list(suite.findall("testsuite"))
    tests = sum(int(item.attrib.get("tests", 0)) for item in suites)
    failures = sum(int(item.attrib.get("failures", 0)) for item in suites)
    errors = sum(int(item.attrib.get("errors", 0)) for item in suites)
    coverage_percent = float(coverage["totals"]["percent_covered"])
    reasons: list[str] = []
    if failures > policy["maximum_failures"]:
        reasons.append(f"{failures} test failure(s) exceeded policy")
    if errors > policy["maximum_errors"]:
        reasons.append(f"{errors} test error(s) exceeded policy")
    if coverage_percent < policy["minimum_coverage_percent"]:
        reasons.append(
            f"{coverage_percent:.2f}% coverage is below "
            f"{policy['minimum_coverage_percent']}%"
        )
    decision = (
        policy["decision_on_failure"] if reasons else policy["decision_on_success"]
    )
    return {
        "decision": decision,
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "coverage_percent": round(coverage_percent, 2),
        "policy": policy,
        "rationale": reasons or ["All test and coverage policies were satisfied."],
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    decision = build_decision(project_root)
    target = project_root / "reports/quality-decision.json"
    target.write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    return 0 if decision["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
