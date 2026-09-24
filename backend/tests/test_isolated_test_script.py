"""The local test launcher must never select an existing container or data volume."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "scripts/test_fresh.py"
    spec = importlib.util.spec_from_file_location("isolated_test_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "compose.yaml").write_text(
        "services:\n  database:\n    image: synthetic-cached-image\n"
    )
    module.ROOT = tmp_path
    monkeypatch.setattr(module.sys, "argv", [str(path), "-q", "tests/test_identity.py"])
    monkeypatch.setattr(module, "quiet", Mock(return_value=SimpleNamespace(returncode=0)))
    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(module.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(
        module.subprocess,
        "run",
        Mock(
            side_effect=[
                SimpleNamespace(returncode=0, stdout="127.0.0.1:54321\n"),
                SimpleNamespace(returncode=0),
            ]
        ),
    )
    monkeypatch.setattr(module, "create_engine", Mock(return_value=MagicMock()))
    return module, process


def test_fresh_launcher_uses_only_owned_ephemeral_resources(launcher):
    module, process = launcher

    def run(args, **kwargs):
        if args[:2] == ["docker", "port"]:
            return SimpleNamespace(returncode=0, stdout="127.0.0.1:54321\n")
        # Restore tests cannot clone PostgreSQL while the readiness pool is connected.
        module.create_engine.return_value.dispose.assert_called_once()
        return SimpleNamespace(returncode=0)

    module.subprocess.run.side_effect = run
    assert module.main() == 0
    args = module.subprocess.Popen.call_args.args[0]
    name = args[args.index("--name") + 1]
    assert name.startswith("elseview-fresh-test-")
    assert "--rm" in args and "--pull=never" in args
    assert args[args.index("--publish") + 1] == "127.0.0.1::5432"
    assert args[args.index("--tmpfs") + 1] == "/var/lib/postgresql/data:rw"
    assert args.count("--mount") == 1 and "--volume" not in args and "-v" not in args
    assert args[args.index("--mount") + 1].endswith("10-init.sh,readonly")
    envfile = Path(args[args.index("--env-file") + 1])
    assert not envfile.is_relative_to(module.ROOT)
    assert not envfile.exists()
    call = module.subprocess.run.call_args
    assert "--fresh" in call.args[0]
    assert call.args[0][-2:] == ["-q", "tests/test_identity.py"]
    assert call.kwargs["env"]["TEST_DATABASE_MODE"] == "fresh"
    assert call.kwargs["env"]["TEST_ALLOW_RESET"] == "elseview_test"
    assert call.kwargs["env"]["AI_MODE"] == "mock"
    module.quiet.assert_called_with("docker", "stop", "--time=5", name)
    process.wait.assert_called_once_with(timeout=15)
    assert not list(module.ROOT.glob(".evdb-*"))


def test_test_failure_is_preserved_and_container_is_still_stopped(launcher):
    module, process = launcher
    module.subprocess.run.side_effect = [
        SimpleNamespace(returncode=0, stdout="127.0.0.1:54321\n"),
        SimpleNamespace(returncode=7),
    ]
    assert module.main() == 7
    assert module.quiet.call_args.args[:3] == ("docker", "stop", "--time=5")
    process.wait.assert_called_once()


def test_missing_cached_image_never_pulls_or_starts_container(launcher):
    module, _ = launcher
    module.quiet.return_value.returncode = 1
    with pytest.raises(RuntimeError, match="already be cached"):
        module.main()
    module.subprocess.Popen.assert_not_called()
    module.subprocess.run.assert_not_called()


def test_startup_failure_stops_only_new_container(launcher):
    module, process = launcher
    process.poll.return_value = 1
    with pytest.raises(RuntimeError, match="failed to start"):
        module.main()
    args = module.subprocess.Popen.call_args.args[0]
    module.quiet.assert_called_with("docker", "stop", "--time=5", args[args.index("--name") + 1])
    module.subprocess.run.assert_not_called()
    process.wait.assert_called_once()
