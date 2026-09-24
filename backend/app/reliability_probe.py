"""Opt-in P18 entry point and dependency-free, aggregate-only measurements."""

import json
import math
import os
import platform
import resource
import sys
from pathlib import Path

from app.test_runner import validate_test_database


def validate_load_environment():
    url = validate_test_database(
        os.environ.get("DATABASE_URL", ""),
        os.environ.get("TEST_DATABASE_URL", ""),
        os.environ.get("TEST_ALLOW_RESET", ""),
    )
    if os.environ.get("TEST_ALLOW_LOAD") != "1":
        raise RuntimeError("P18 requires TEST_ALLOW_LOAD=1 and exclusive test database ownership")
    output = Path(os.environ.get("P18_METRICS_PATH", ""))
    if not output.is_absolute() or output.suffix != ".json":
        raise RuntimeError("P18_METRICS_PATH must be an absolute .json path")
    return url, output


def percentile(values, percent):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)]


def peak_rss_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def hardware():
    return {
        "os": platform.system(),
        "architecture": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
    }


def write_metrics(path, metrics):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main():
    import pytest

    url, _ = validate_load_environment()
    os.environ.update(
        TEST_ALLOW_DB="1",
        MIGRATION_DATABASE_URL=url,
        AI_MODE="mock",
        APP_ENV="test",
        JOB_RUNNER_ENABLED="false",
    )
    os.chdir(Path(__file__).resolve().parents[1])
    return pytest.main(["tests/test_reliability.py", "-m", "load", "-q"])


if __name__ == "__main__":
    sys.exit(main())
