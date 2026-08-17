from pathlib import Path
from tomllib import loads

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_python_series_is_explicitly_locked() -> None:
    assert (PROJECT_ROOT / ".python-version").read_text().strip() == "3.12"
    project = loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert project["project"]["requires-python"] == ">=3.12,<3.13"


def test_direct_dependencies_are_exactly_pinned() -> None:
    project = loads((PROJECT_ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    test_dependencies = project["project"]["optional-dependencies"]["test"]

    assert dependencies
    assert test_dependencies
    assert all("==" in requirement for requirement in dependencies)
    assert all("==" in requirement for requirement in test_dependencies)


def test_api_quality_tools_are_part_of_the_contract() -> None:
    project = loads((PROJECT_ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]
    test_dependencies = project["project"]["optional-dependencies"]["test"]

    assert "httpx==0.28.1" in dependencies
    assert "jsonschema==4.26.0" in dependencies
    assert "respx==0.23.1" in test_dependencies
    assert "schemathesis==4.24.3" in test_dependencies
    assert "pytest-xdist==3.8.0" in test_dependencies
