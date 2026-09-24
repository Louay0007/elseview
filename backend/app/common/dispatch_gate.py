"""Single-process send barrier, after DB workspace lock and before mutation.

The sender transfers its lease out of a committed authorization transaction and
releases it when request bytes have finished sending, BEFORE waiting for response
or opening any other DB transaction. This lock never replaces DB authorization.
Direct SQL writers and multi-process deployments require a different dispatcher.
"""

import threading
import weakref

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.common.errors import DomainError

_mutex = threading.Lock()
_buckets = weakref.WeakValueDictionary()
_KEY = "elseview_dispatch_leases"


class _Bucket:
    def __init__(self):
        self.lock = threading.Lock()


class Lease:
    def __init__(self, bucket):
        self.bucket = bucket
        self._guard = threading.Lock()
        self.released = False

    def release(self):
        with self._guard:
            if not self.released:
                self.released = True
                self.bucket.lock.release()


def acquire_for_session(session, workspace_id):
    key = str(workspace_id)
    leases = session.info.setdefault(_KEY, {})
    if key in leases:
        return leases[key]
    with _mutex:
        bucket = _buckets.get(key)
        if bucket is None:
            bucket = _Bucket()
            _buckets[key] = bucket
    if not bucket.lock.acquire(timeout=35):
        raise DomainError("DISPATCH_BUSY", "An outbound send is completing. Retry shortly.", 503)
    lease = Lease(bucket)
    leases[key] = lease
    return lease


def transfer(session, workspace_id):
    """Caller must release the returned lease even if transaction commit fails."""
    return session.info[_KEY].pop(str(workspace_id))


@event.listens_for(Session, "after_transaction_end")
def _release_on_transaction_end(session, transaction):
    if transaction.parent is None:
        for lease in session.info.pop(_KEY, {}).values():
            lease.release()
