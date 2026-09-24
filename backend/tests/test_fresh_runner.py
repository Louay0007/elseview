"""The disposable runner's safety defaults also apply when pytest options are supplied."""

import runpy
from pathlib import Path

import pytest

_options = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/test_fresh.py"))[
    "test_options"
]


@pytest.mark.parametrize("arguments", [[], ["-q"], ["tests/test_db.py", "--tb=short"]])
def test_fresh_default_exclusions_survive_selectors(arguments):
    original = list(arguments)
    enabled, selectors = _options(arguments)
    assert enabled is False
    assert selectors == ["-m", "not live_llm and not load and not cache and not browser", *original]
    assert arguments == original


def test_fresh_cache_opt_in_is_not_forwarded_to_pytest():
    enabled, selectors = _options(["--with-cache", "-q", "tests/test_cache_idempotency.py"])
    assert enabled is True
    assert selectors == [
        "-m",
        "not live_llm and not load and not browser",
        "-q",
        "tests/test_cache_idempotency.py",
    ]


def test_explicit_marker_selection_remains_available_for_operator_drills():
    enabled, selectors = _options(["--with-cache", "-m", "load"])
    assert enabled is True
    assert selectors == ["-m", "not live_llm and not load and not browser", "-m", "load"]


def test_browser_opt_in_enables_only_disposable_cache_and_live_browser_tests():
    enabled, selectors = _options(["--with-browser", "-q"])
    assert enabled is True
    assert selectors == ["-m", "not live_llm and not load", "-q"]
