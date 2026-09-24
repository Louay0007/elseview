"""Run backend tests against a new RAM-backed PostgreSQL container, never a shared database.

Invoke with backend/.venv/bin/python scripts/test_fresh.py [pytest selectors/options].
Requires Docker and the repository-pinned PostgreSQL image already cached locally.
Pass --with-cache to also start an isolated pinned Valkey for cache-marked tests.
Pass --with-browser to include installed-Chrome journeys and their isolated cache.
"""

import os
import secrets
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import yaml
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]


def quiet(*args):
    return subprocess.run(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )


def test_options(arguments):
    with_browser = "--with-browser" in arguments
    with_cache = with_browser or "--with-cache" in arguments
    selectors = [
        argument
        for argument in arguments
        if argument not in {"--with-cache", "--with-browser"}
    ]
    marker = "not live_llm and not load"
    if not with_cache:
        marker += " and not cache"
    if not with_browser:
        marker += " and not browser"
    return with_cache, ["-m", marker, *selectors]


@contextmanager
def fresh_cache(compose, scratch, enabled):
    if not enabled:
        yield None
        return
    image = compose["services"]["cache"]["image"]
    if quiet("docker", "image", "inspect", image).returncode:
        raise RuntimeError("The pinned Valkey image must already be cached locally")
    name = "elseview-fresh-cache-" + uuid4().hex
    password = secrets.token_hex(32)
    config = Path(scratch) / "cache.conf"
    descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(
            'bind 0.0.0.0\nport 6379\nsave ""\nappendonly no\n'
            "maxmemory 64mb\nmaxmemory-policy noeviction\n"
            f"requirepass {password}\n"
        )
    process = subprocess.Popen(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--label",
            "elseview.purpose=disposable-test",
            "--memory=128m",
            "--cpus=1",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--publish",
            "127.0.0.1::6379",
            "--mount",
            f"type=bind,source={config},target=/tmp/test-cache.conf,readonly",
            "--entrypoint",
            "valkey-server",
            image,
            "/tmp/test-cache.conf",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client = None
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Disposable Valkey container failed to start")
            ports = subprocess.run(
                ["docker", "port", name, "6379/tcp"],
                capture_output=True,
                text=True,
                check=False,
            )
            if ports.returncode == 0 and ports.stdout.startswith("127.0.0.1:"):
                port = int(ports.stdout.strip().rsplit(":", 1)[1])
                client = Redis(
                    host="127.0.0.1",
                    port=port,
                    password=password,
                    socket_timeout=1,
                    socket_connect_timeout=1,
                )
                try:
                    if client.ping():
                        break
                except RedisError:
                    pass
                client.close()
                client = None
            time.sleep(0.25)
        else:
            raise RuntimeError("Disposable Valkey did not become ready")
        print(
            "Fresh isolated Valkey is responsive; no shared cache is used.", flush=True
        )
        yield f"redis://:{password}@127.0.0.1:{port}/15"
    finally:
        if client is not None:
            client.close()
        quiet("docker", "stop", "--time=5", name)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)


def main():
    with_cache, selectors = test_options(sys.argv[1:])
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    image = compose["services"]["database"]["image"]
    if quiet("docker", "image", "inspect", image).returncode:
        raise RuntimeError("The pinned PostgreSQL image must already be cached locally")
    name = "elseview-fresh-test-" + uuid4().hex
    with (
        tempfile.TemporaryDirectory(prefix="elseview-test-") as private_scratch,
        tempfile.TemporaryDirectory(prefix=".evdb-", dir=ROOT) as scratch,
    ):
        scratch = Path(scratch)
        passwords = {
            key: secrets.token_hex(32)
            for key in (
                "POSTGRES_PASSWORD",
                "DB_OWNER_PASSWORD",
                "DB_APP_PASSWORD",
                "DB_TEST_PASSWORD",
            )
        }
        envfile = Path(private_scratch) / "postgres.env"
        descriptor = os.open(envfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            for key, value in {
                **passwords,
                "POSTGRES_USER": "postgres",
                "POSTGRES_DB": "postgres",
                "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256",
            }.items():
                stream.write(f"{key}={value}\n")
        process = subprocess.Popen(
            [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "--name",
                name,
                "--label",
                "elseview.purpose=disposable-test",
                "--memory=768m",
                "--cpus=2",
                "--tmpfs",
                "/var/lib/postgresql/data:rw",
                "--publish",
                "127.0.0.1::5432",
                "--env-file",
                str(envfile),
                "--mount",
                f"type=bind,source={ROOT / 'infra/postgres/init.sh'},target=/docker-entrypoint-initdb.d/10-init.sh,readonly",
                image,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        engine = None
        try:
            deadline = time.monotonic() + 60
            test_url = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(
                        "Disposable PostgreSQL container failed to start"
                    )
                ports = subprocess.run(
                    ["docker", "port", name, "5432/tcp"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if ports.returncode == 0 and ports.stdout.startswith("127.0.0.1:"):
                    port = int(ports.stdout.strip().rsplit(":", 1)[1])
                    test_url = URL.create(
                        "postgresql+psycopg",
                        username="test_owner",
                        password=passwords["DB_TEST_PASSWORD"],
                        host="127.0.0.1",
                        port=port,
                        database="elseview_test",
                    )
                    engine = create_engine(
                        test_url,
                        hide_parameters=True,
                        connect_args={"connect_timeout": 1},
                    )
                    try:
                        with engine.connect() as connection:
                            connection.execute(text("SELECT 1"))
                        break
                    except SQLAlchemyError:
                        engine.dispose()
                        engine = None
                time.sleep(0.25)
            else:
                raise RuntimeError("Disposable PostgreSQL did not become ready")
            engine.dispose()
            engine = None
            print(
                "Fresh isolated PostgreSQL is responsive; no existing database or volume is mounted.",
                flush=True,
            )
            env = os.environ.copy()
            env.update(
                {
                    "DATABASE_URL": test_url.set(
                        username="app",
                        password=passwords["DB_APP_PASSWORD"],
                        database="elseview_app",
                    ).render_as_string(hide_password=False),
                    "TEST_DATABASE_URL": test_url.render_as_string(hide_password=False),
                    "MIGRATION_DATABASE_URL": test_url.render_as_string(
                        hide_password=False
                    ),
                    "TEST_ALLOW_RESET": "elseview_test",
                    "TEST_DATABASE_MODE": "fresh",
                    "AI_MODE": "mock",
                    "JOB_RUNNER_ENABLED": "false",
                    "MAIL_MODE": "local",
                    "COLLABORATION_INTEGRATION_MODE": "disabled",
                }
            )
            with fresh_cache(compose, private_scratch, with_cache) as cache_url:
                env.pop("CACHE_URL", None)
                if cache_url is not None:
                    env["CACHE_URL"] = cache_url
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "app.test_runner",
                        "--fresh",
                        "--basetemp=" + str(scratch / "t"),
                        *selectors,
                    ],
                    cwd=ROOT / "backend",
                    env=env,
                    check=False,
                )
                return result.returncode
        finally:
            if engine is not None:
                engine.dispose()
            quiet("docker", "stop", "--time=5", name)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError):
        print(
            "Fresh test infrastructure could not complete; no shared database was reset.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
