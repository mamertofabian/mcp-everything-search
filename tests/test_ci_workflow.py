"""Behavioral tests for the CI workflow contract.

CI must run the test suite on every supported OS and Python bound, and run
lint/format/type checks on every source file covered by an active MAID
manifest. Brownfield files without coverage are excluded until a manifest
brings them in. Failures must never be masked.
"""

from pathlib import Path
from typing import Any, Dict, List, Set

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
JOBS = ["test", "quality"]


def _workflow() -> Dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job(name: str) -> Dict[str, Any]:
    return _workflow()["jobs"][name]


def _run_lines(job: Dict[str, Any]) -> List[str]:
    return [
        line.strip()
        for step in job["steps"]
        if "run" in step
        for line in step["run"].splitlines()
        if line.strip()
    ]


def _uses(job: Dict[str, Any]) -> List[str]:
    return [step["uses"].split("@")[0] for step in job["steps"] if "uses" in step]


def _setup_uv_step(job: Dict[str, Any]) -> Dict[str, Any]:
    return next(
        s for s in job["steps"] if s.get("uses", "").startswith("astral-sh/setup-uv@")
    )


def _manifest_covered_sources() -> Set[str]:
    covered: Set[str] = set()
    for manifest in (ROOT / "manifests").glob("*.manifest.yaml"):
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        files = data.get("files", {})
        for section in ("create", "edit", "scope"):
            for entry in files.get(section, []):
                path = entry["path"]
                if path.startswith("src/") and path.endswith(".py"):
                    covered.add(path)
    return covered


def test_ci_runs_on_pushes_to_main_and_pull_requests():
    # Arrange
    workflow = _workflow()

    # Act: yaml parses the bare "on" key as boolean True
    triggers = workflow.get("on", workflow.get(True))

    # Assert
    assert triggers["push"]["branches"] == ["main"]
    assert "pull_request" in triggers


def test_ci_is_read_only_and_cancels_superseded_runs():
    workflow = _workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_ci_runs_tests_from_lockfile_on_windows_macos_and_linux():
    # Arrange
    job = _job("test")
    lines = _run_lines(job)

    # Assert
    assert set(job["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "windows-latest",
        "macos-latest",
    }
    assert job["runs-on"] == "${{ matrix.os }}"
    assert lines.index("uv sync --locked") < lines.index("uv run pytest -q")


def test_ci_tests_the_lowest_and_a_current_python():
    # Arrange
    job = _job("test")

    # Act
    versions = job["strategy"]["matrix"]["python-version"]
    setup_python = _setup_uv_step(job)["with"]["python-version"]

    # Assert
    assert "3.10" in versions and "3.13" in versions
    assert setup_python == "${{ matrix.python-version }}"


@pytest.mark.parametrize("name", JOBS)
def test_ci_jobs_check_out_code_and_install_uv(name):
    uses = _uses(_job(name))

    assert uses[:2] == ["actions/checkout", "astral-sh/setup-uv"]


@pytest.mark.parametrize("name", JOBS)
def test_ci_jobs_never_mask_or_skip_failures(name):
    # Arrange
    job = _job(name)
    nodes = [job, *job["steps"]]

    # Act
    masked = [n for n in nodes if n.get("continue-on-error") or "if" in n]
    swallowed = [line for line in _run_lines(job) if "||" in line or "set +e" in line]

    # Assert
    assert masked == []
    assert swallowed == []


def test_ci_quality_checks_cover_every_manifest_covered_source_file():
    # Arrange
    job = _job("quality")
    checked_paths = set(job["env"]["MAID_COVERED_PATHS"].split())

    # Act
    missing = _manifest_covered_sources() - checked_paths

    # Assert
    assert missing == set()
    assert "tests" in checked_paths


def test_ci_quality_job_runs_lint_format_types_and_maid_validation_in_bash():
    # Arrange
    job = _job("quality")

    # Act
    lines = _run_lines(job)

    # Assert: bash word-splits $MAID_COVERED_PATHS; an empty expansion would check the whole repo
    assert job["runs-on"] == "ubuntu-latest"
    assert job["defaults"]["run"]["shell"] == "bash"
    assert lines.index("uv sync --locked") < lines.index(
        "uv run ruff check $MAID_COVERED_PATHS"
    )
    assert "uv run ruff format --check $MAID_COVERED_PATHS" in lines
    assert "uv run pyright $MAID_COVERED_PATHS" in lines
    assert "scripts/maid validate" in lines


def test_ci_pins_the_maid_runner_version():
    spec = _job("quality")["env"]["MAID_RUNNER_SPEC"]

    assert spec.startswith("maid-runner[all]==")
