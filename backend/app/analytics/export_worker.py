"""One bounded, memory-only render per process. No database or network access."""

import json
import resource
import sys

from .exports import MAX_INPUT_BYTES, ExportFontError, ExportLimit, render_document


def _deny_network(event, args):
    if event.startswith("socket.") or event == "urllib.Request":
        raise PermissionError("Network is disabled in document rendering")


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # Linux/Docker enforces address-space limits. macOS rejects RLIMIT_AS/DATA;
    # native development retains input/row/page/output/CPU/wall-time bounds only.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    sys.addaudithook(_deny_network)
    try:
        content = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(content) > MAX_INPUT_BYTES:
            raise ExportLimit
        output = render_document(json.loads(content), sys.argv[1])
        sys.stdout.buffer.write(output)
        return 0
    except (ExportLimit, MemoryError, RecursionError, OverflowError):
        return 2
    except ExportFontError:
        return 3
    except Exception:
        # Neither source text nor filesystem paths enter logs or API errors.
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
