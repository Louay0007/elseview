#!/usr/bin/env python3
"""Detach the Vite dev server so it survives the tool-call process group.

Resolves pnpm from PATH at run time. An absolute interpreter path would pin
this script to one machine and break for every other developer and for CI.

    python3 scripts/run_frontend_detached.py
    tail -f /tmp/elseview-vite.log
"""
import os
import shutil
import signal
import sys

LOG = "/tmp/elseview-vite.log"
FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
PNPM = shutil.which("pnpm")
if not PNPM:
    sys.exit("pnpm not found on PATH. Install Node.js 24 and pnpm, then retry.")

# First fork: parent returns immediately.
if os.fork() > 0:
    sys.exit(0)

os.setsid()  # detach from the controlling terminal / process group

# Second fork: ensure we can never re-acquire a controlling terminal.
if os.fork() > 0:
    sys.exit(0)

signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)

os.chdir(FRONTEND)
os.umask(0o022)

log_fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
os.dup2(log_fd, 1)
os.dup2(log_fd, 2)
devnull = os.open(os.devnull, os.O_RDONLY)
os.dup2(devnull, 0)

env = dict(os.environ)

os.execve(PNPM, [PNPM, "dev", "--host", "127.0.0.1", "--port", "8080", "--strictPort"], env)
