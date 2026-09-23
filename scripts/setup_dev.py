#!/usr/bin/env python3
"""Create local hex64 secrets once; never overwrite credentials or reset data."""

import os
from pathlib import Path
import secrets
import sys


def main() -> int:
    destination = Path(__file__).resolve().parent.parent / ".env"
    names = (
        "POSTGRES_PASSWORD",
        "DB_OWNER_PASSWORD",
        "DB_APP_PASSWORD",
        "DB_TEST_PASSWORD",
        "CACHE_PASSWORD",
        "SECRET_KEY",
    )
    content = "# Local development secrets. Do not commit or share.\n"
    content += "".join(f"{name}={secrets.token_hex(32)}\n" for name in names)
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Refusing to overwrite {destination}. Existing credentials unchanged.", file=sys.stderr)
        return 1
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(content)
    print(f"Created {destination} (0600). No services started or data changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())