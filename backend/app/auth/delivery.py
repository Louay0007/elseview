"""Development-only private mail spool: no token in HTTP responses or operational logs."""

import json
import os
import time
from uuid import uuid4

from app.common.errors import DomainError


def deliver_local(settings, email, purpose, token):
    if settings.app_env not in {"development", "test"}:
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is not configured.", 503)
    root = settings.private_root / "dev-mail"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    # Development mailbox is intentionally private and short-lived, not a notification service.
    for old in root.glob("*.json"):
        if old.stat().st_mtime < time.time() - 86400:
            old.unlink(missing_ok=True)
    if sum(1 for _ in root.glob("*.json")) >= 1000:
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is temporarily unavailable.", 503)
    path = root / f"{uuid4()}.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump({"recipient": email, "purpose": purpose, "token": token}, output)
