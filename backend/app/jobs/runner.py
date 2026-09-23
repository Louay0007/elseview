"""Single-flight worker. Database transactions always execute off the event loop."""

import asyncio
import logging

from app.jobs import service

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, database, settings):
        self.database = database
        self.poll = max(0.05, getattr(settings, "job_poll_seconds", 2))
        self.lease = max(1, getattr(settings, "job_lease_seconds", 30))
        self.timeout = max(0.05, getattr(settings, "job_timeout_seconds", 10))
        self.shutdown = max(0.05, getattr(settings, "job_shutdown_seconds", 3))
        self._stop = asyncio.Event()
        self._task = None
        self._handler = None
        self._quarantined = False

    @staticmethod
    def _observe(task):
        """Retrieve even late cancellation-cleanup errors without exposing their text."""
        if not task.cancelled():
            task.exception()

    async def _cancel_handler(self):
        task = self._handler
        if task is None:
            return True
        if not task.done():
            task.cancel()
            await asyncio.wait({task}, timeout=min(self.shutdown, 0.1))
        if task.done():
            self._observe(task)
            self._handler = None
            return True
        # Python cannot forcibly stop a coroutine that suppresses cancellation.
        # Permanently stop this worker, retain the lease, and observe its eventual exit.
        self._quarantined = True
        self._stop.set()
        return False

    def _transaction(self, function, *args, **kwargs):
        with self.database.sessions() as session, session.begin():
            value = function(session, *args, **kwargs)
            if isinstance(value, service.Job):
                session.flush()
                session.expunge(value)
            return value

    async def _db(self, function, *args, **kwargs):
        return await asyncio.to_thread(self._transaction, function, *args, **kwargs)

    async def start(self):
        if self._quarantined or (self._handler is not None and not self._handler.done()):
            return
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="job-runner")
            self._task.add_done_callback(self._observe)

    async def stop(self):
        self._stop.set()
        if self._task is None:
            return
        done, _ = await asyncio.wait({self._task}, timeout=self.shutdown)
        if not done:
            self._task.cancel()
            # Cancellation leaves an expiring lease, never releases an in-flight DB call.
            await asyncio.wait({self._task}, timeout=0.15)

    async def _execute(self, job):
        handler = service.REGISTRY[job.kind][0]
        self._handler = asyncio.create_task(handler(job.payload))
        self._handler.add_done_callback(self._observe)
        deadline = asyncio.get_running_loop().time() + self.timeout
        try:
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    if await self._cancel_handler():
                        await self._db(
                            service.fail, job.id, job.lease_token, "handler_timeout", True
                        )
                    return
                done, _ = await asyncio.wait(
                    {self._handler}, timeout=min(self.lease / 3, remaining)
                )
                if done:
                    try:
                        result = self._handler.result()
                    except Exception:
                        await self._db(
                            service.fail, job.id, job.lease_token, "handler_error", False
                        )
                    else:
                        await self._db(service.complete, job.id, job.lease_token, result)
                    return
                if not await self._db(service.heartbeat, job.id, job.lease_token, self.lease):
                    return
        finally:
            if not self._quarantined:
                await self._cancel_handler()

    async def _run(self):
        while not self._stop.is_set():
            try:
                job = await self._db(service.claim, self.lease)
                if job:
                    await self._execute(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                # Never log handler payloads or exception text (potential PII).
                logger.warning("Job runner operation failed")
            # Sleep even after work/errors: no empty/error/invalid-queue hot loop.
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll)
            except TimeoutError:
                pass
