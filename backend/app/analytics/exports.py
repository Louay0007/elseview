"""Bounded, stateless document exports of already-authorized snapshot data.

PDF uses local Unicode fonts and HarfBuzz (no HTML, assets, links or remote fetch).
Docker supplies DejaVu Sans and its license via fonts-dejavu-core. Native developers
can set REPORT_EXPORT_FONT to a locally installed, legally embeddable TTF font.
Each download reconstructs data; no derivative file, cleanup job or storage grant
exists. Previously downloaded copies cannot be recalled. Limits fail closed rather
than truncating original answers, numeric denominators or provenance.
"""

import io
import json
import math
import os
import subprocess
import sys
import threading
import unicodedata
from pathlib import Path

from app.common.errors import DomainError

MEDIA_TYPES = {
    "json": "application/json",
    "csv": "text/csv",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_INPUT_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5000
MAX_DEPTH = 30
MAX_CELL_CHARS = 16000
MAX_PAGES = 80
RENDER_SECONDS = 20
_SLOTS = threading.BoundedSemaphore(2)


class ExportLimit(ValueError):
    pass


class ExportFontError(ValueError):
    pass


def encode_document(data):
    # iterencode bounds serialization even before the worker is started.
    result = bytearray()
    for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True).iterencode(
        data
    ):
        if len(chunk) > MAX_INPUT_BYTES:
            raise ExportLimit
        result.extend(chunk.encode("utf-8"))
        if len(result) > MAX_INPUT_BYTES:
            raise ExportLimit
    return bytes(result)


def document_rows(data):
    """JSON Pointer paths avoid collisions between participant-controlled keys."""
    rows = 0
    nodes = 0

    def visit(value, path, depth):
        nonlocal rows, nodes
        nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_ROWS * 4 or len(path) > MAX_CELL_CHARS:
            raise ExportLimit
        if isinstance(value, dict) and value:
            if len(value) > MAX_ROWS:
                raise ExportLimit
            for key in sorted(value):
                if not isinstance(key, str) or len(key) > MAX_CELL_CHARS:
                    raise ExportLimit
                escaped = key.replace("~", "~0").replace("/", "~1")
                yield from visit(value[key], path + "/" + escaped, depth + 1)
            return
        if isinstance(value, list) and value:
            if len(value) > MAX_ROWS:
                raise ExportLimit
            for index, item in enumerate(value):
                yield from visit(item, path + "/" + str(index), depth + 1)
            return
        if isinstance(value, str):
            kind = "string"
            if len(value) > MAX_CELL_CHARS:
                raise ExportLimit
        elif isinstance(value, bool):
            kind = "boolean"
        elif isinstance(value, (int, float)):
            if not math.isfinite(value):
                raise ExportLimit
            kind = "number"
            # Excel cannot represent integers beyond 15 digits exactly.
            if isinstance(value, int) and abs(value) >= 10**15:
                kind, value = "integer", str(value)
        elif value is None:
            kind, value = "null", "null"
        elif value == []:
            kind, value = "array", "[]"
        elif value == {}:
            kind, value = "object", "{}"
        else:
            raise ExportLimit
        rows += 1
        if rows > MAX_ROWS:
            raise ExportLimit
        yield path, kind, value

    yield from visit(data, "", 0)


def font_path():
    path = Path(
        os.environ.get("REPORT_EXPORT_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    if not path.is_absolute() or not path.is_file():
        raise ExportFontError
    return path


def _xlsx(rows):
    import xlsxwriter

    output = io.BytesIO()
    with xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "strings_to_numbers": False,
        },
    ) as workbook:
        sheet = workbook.add_worksheet("Report")
        header = workbook.add_format({"bold": True, "bg_color": "#E8EEF4"})
        text_format = workbook.add_format({"text_wrap": True, "valign": "top"})
        rtl_format = workbook.add_format({"text_wrap": True, "valign": "top", "reading_order": 2})
        sheet.freeze_panes(1, 0)
        sheet.set_column(0, 0, 65)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 2, 80)
        for col, value in enumerate(("Path (JSON Pointer)", "Type", "Value")):
            sheet.write_string(0, col, value, header)
        for index, (path, kind, value) in enumerate(rows, 1):
            sheet.write_string(index, 0, path, text_format)
            sheet.write_string(index, 1, kind)
            if kind == "number":
                sheet.write_number(index, 2, value)
            elif kind == "boolean":
                sheet.write_boolean(index, 2, value)
            else:
                # Always explicit strings: formulas/URLs and leading controls stay inert.
                fmt = (
                    rtl_format
                    if any(unicodedata.bidirectional(c) in {"R", "AL"} for c in value)
                    else text_format
                )
                if sheet.write_string(index, 2, value, fmt) != 0:
                    raise ExportLimit
    return output.getvalue()


def _pdf(data, rows):
    from fpdf import FPDF

    class BoundedPDF(FPDF):
        def add_page(self, *args, **kwargs):
            if self.pages_count >= MAX_PAGES:
                raise ExportLimit
            return super().add_page(*args, **kwargs)

    pdf = BoundedPDF()
    pdf.add_font("Report", fname=str(font_path()))
    pdf.set_font("Report", size=10)
    pdf.set_text_shaping(True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title("Research report")
    pdf.add_page()
    pdf.multi_cell(0, 7, "Research report", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(
        0,
        5,
        "Original snapshot values; paths use JSON Pointer. Original data is attached as JSON.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    cmap = pdf.current_font.cmap
    for path, kind, value in rows:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        for part in (path, text):
            # Do not silently drop unsupported glyphs. JSON/XLSX remain available.
            if any(
                ord(c) not in cmap and c not in "\n\r\t" and unicodedata.category(c) != "Cf"
                for c in part
            ):
                raise ExportFontError
        pdf.ln(2)
        pdf.set_text_color(75, 85, 100)
        pdf.multi_cell(
            0, 5, path + " [" + kind + "]", new_x="LMARGIN", new_y="NEXT", wrapmode="CHAR"
        )
        pdf.set_text_color(0)
        pdf.multi_cell(
            0,
            6,
            text,
            new_x="LMARGIN",
            new_y="NEXT",
            wrapmode="CHAR",
            align="R" if _is_rtl(text) else "L",
        )
    pdf.embed_file(
        bytes=encode_document(data),
        basename="report-data.json",
        mime_type="application/json",
        desc="Original authorized snapshot data",
        compress=True,
    )
    return bytes(pdf.output())


def _is_rtl(text):
    for character in text:
        direction = unicodedata.bidirectional(character)
        if direction in {"R", "AL", "L"}:
            return direction != "L"
    return False


def render_document(data, format):
    encode_document(data)
    rows = list(document_rows(data))
    if format not in {"pdf", "xlsx"}:
        raise ValueError("Unsupported document format")
    content = _pdf(data, rows) if format == "pdf" else _xlsx(rows)
    if len(content) > MAX_OUTPUT_BYTES:
        raise ExportLimit
    return content


def generate_document(data, format):
    """Sync routes call this in a thread; child CPU/memory/wall-time are bounded."""
    try:
        payload = encode_document(data)
        list(document_rows(data))
    except (ExportLimit, ValueError, RecursionError, OverflowError) as exc:
        raise DomainError(
            "EXPORT_TOO_LARGE", "Report exceeds document export limits. Use JSON or CSV.", 413
        ) from exc
    if format not in {"pdf", "xlsx"}:
        raise DomainError("INVALID_EXPORT", "Unsupported document format.", 422)
    if not _SLOTS.acquire(blocking=False):
        raise DomainError("EXPORT_BUSY", "Document rendering is busy. Retry shortly.", 503)
    try:
        # Pass no app secrets to the text-only worker, and never participant values in argv.
        env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        if "REPORT_EXPORT_FONT" in os.environ:
            env["REPORT_EXPORT_FONT"] = os.environ["REPORT_EXPORT_FONT"]
        try:
            result = subprocess.run(
                [sys.executable, "-m", "app.analytics.export_worker", format],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=RENDER_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DomainError(
                "EXPORT_TIMEOUT", "Document rendering timed out. Retry with a smaller report.", 503
            ) from exc
        except OSError as exc:
            raise DomainError(
                "EXPORT_RENDER_FAILED", "Document rendering is unavailable. Retry shortly.", 503
            ) from exc
        if result.returncode == 2 or len(result.stdout) > MAX_OUTPUT_BYTES:
            raise DomainError(
                "EXPORT_TOO_LARGE", "Report exceeds document export limits. Use JSON or CSV.", 413
            )
        if result.returncode == 3:
            raise DomainError(
                "EXPORT_FONT_UNAVAILABLE",
                "A local font supporting the report text is required. Use JSON or XLSX.",
                503,
            )
        if result.returncode or not result.stdout:
            raise DomainError(
                "EXPORT_RENDER_FAILED", "Document rendering failed. Retry shortly.", 503
            )
        return result.stdout
    finally:
        _SLOTS.release()
