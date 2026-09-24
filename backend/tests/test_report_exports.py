"""Stateless export rendering; no database or external network required."""

import io
import json
import re
import subprocess
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from app.analytics.exports import ExportLimit, document_rows, render_document

pytestmark = pytest.mark.unit


def test_rows_preserve_original_text_numbers_and_unambiguous_paths():
    data = {"a/b": {"~text": "العربية café 3arabi"}, "metrics": {"denominator": 12}}
    assert list(document_rows(data)) == [
        ("/a~1b/~0text", "string", "العربية café 3arabi"),
        ("/metrics/denominator", "number", 12),
    ]


def test_xlsx_is_real_numeric_and_never_interprets_formulas_or_urls():
    text = '=HYPERLINK("https://invalid.example", "العربية café")'
    content = render_document({"original": text, "count": 12}, "xlsx")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        assert not sheet.findall(".//s:f", ns)
        assert not sheet.findall(".//s:hyperlink", ns)
        assert sheet.find(".//s:c[@r='C2']/s:v", ns).text == "12"
        strings = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        assert text in [e.text for e in strings.findall(".//s:t", ns)]
        assert not any("externalLink" in name for name in archive.namelist())


def test_deep_or_large_documents_fail_without_truncation():
    data = {"value": "x" * 40000}
    with pytest.raises(ExportLimit):
        list(document_rows(data))
    data = {}
    for _ in range(40):
        data = {"nested": data}
    with pytest.raises(ExportLimit):
        list(document_rows(data))


def test_nonfinite_values_are_rejected():
    with pytest.raises((ExportLimit, ValueError)):
        render_document({"bad": float("nan")}, "xlsx")


def test_empty_values_remain_distinguishable():
    assert list(document_rows({"a": [], "b": {}, "c": None, "d": False})) == [
        ("/a", "array", "[]"),
        ("/b", "object", "{}"),
        ("/c", "null", "null"),
        ("/d", "boolean", False),
    ]


@pytest.fixture
def local_pdf_font(monkeypatch):
    from app.analytics.exports import ExportFontError, font_path

    try:
        return font_path()
    except ExportFontError:
        local = Path("/Library/Fonts/Arial Unicode.ttf")
        if not local.is_file():
            pytest.skip(
                "PDF acceptance requires an installed Unicode font; Docker supplies DejaVu Sans"
            )
        monkeypatch.setenv("REPORT_EXPORT_FONT", str(local))
        return local


def test_pdf_actual_document_embeds_exact_original_data_and_unicode_font(local_pdf_font):
    from app.analytics.exports import generate_document

    data = {
        "original": "مرحبا بالعالم العربية café 3arabi",
        "denominator": 12,
        "provenance": "self_report",
    }
    content = generate_document(data, "pdf")
    assert content.startswith(b"%PDF-") and content.rstrip().endswith(b"%%EOF")
    assert b"/FontFile2" in content and b"/ToUnicode" in content
    assert b"report-data.json" in content
    assert not any(key in content for key in (b"/JavaScript", b"/URI", b"/Launch"))
    originals = []
    for stream in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", content, re.DOTALL):
        try:
            originals.append(json.loads(zlib.decompress(stream)))
        except (zlib.error, UnicodeDecodeError, json.JSONDecodeError):
            pass
    assert data in originals


@pytest.mark.parametrize(
    "text", ["=1", "+1", "-2", "@user", "  =1", "\t=1", "\n=1", "\r=1", "https://invalid.example"]
)
def test_xlsx_untrusted_keys_and_values_are_literal_strings(text):
    content = render_document({text: text}, "xlsx")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml")
        assert b"<f>" not in sheet and b"<hyperlink" not in sheet
        assert b'TargetMode="External"' not in b"".join(archive.read(n) for n in archive.namelist())


def test_large_integer_never_silently_rounds_in_excel():
    assert list(document_rows({"id": 12345678901234567})) == [
        ("/id", "integer", "12345678901234567")
    ]


def test_worker_generates_xlsx_and_does_not_inherit_secrets(monkeypatch):
    from app.analytics import exports

    original = exports.subprocess.run

    def run(args, **kwargs):
        assert args[-1] == "xlsx" and "original" not in " ".join(args)
        assert "SECRET_KEY" not in kwargs["env"]
        assert kwargs["timeout"] == exports.RENDER_SECONDS
        return original(args, **kwargs)

    monkeypatch.setenv("SECRET_KEY", "synthetic-not-a-secret")
    monkeypatch.setattr(exports.subprocess, "run", run)
    assert exports.generate_document({"original": "café العربية"}, "xlsx").startswith(b"PK")


def test_worker_network_audit_rejects_attempts():
    from app.analytics.export_worker import _deny_network

    for event in ("socket.connect", "socket.getaddrinfo", "urllib.Request"):
        with pytest.raises(PermissionError):
            _deny_network(event, ())
    _deny_network("open", ())


def test_limits_and_timeout_allow_subsequent_retry(monkeypatch):
    from app.analytics import exports
    from app.common.errors import DomainError

    with pytest.raises(DomainError) as error:
        exports.generate_document({"x": "a" * (exports.MAX_INPUT_BYTES + 1)}, "xlsx")
    assert error.value.code == "EXPORT_TOO_LARGE"
    with monkeypatch.context() as patch:

        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("renderer", 20)

        patch.setattr(exports.subprocess, "run", timeout)
        with pytest.raises(DomainError) as error:
            exports.generate_document({}, "xlsx")
        assert error.value.code == "EXPORT_TIMEOUT"
    assert exports.generate_document({}, "xlsx").startswith(b"PK")


def test_page_and_row_limits_reject_not_truncate(monkeypatch, local_pdf_font):
    from app.analytics import exports

    with pytest.raises(ExportLimit):
        list(document_rows(list(range(exports.MAX_ROWS + 1))))
    monkeypatch.setattr(exports, "MAX_PAGES", 1)
    with pytest.raises(ExportLimit):
        render_document({"value": "Long text " * 1000}, "pdf")


def test_output_limit_is_fail_closed(monkeypatch):
    from app.analytics import exports

    monkeypatch.setattr(exports, "MAX_OUTPUT_BYTES", 1)
    with pytest.raises(ExportLimit):
        render_document({}, "xlsx")


def test_binary_export_body_and_sync_download_contract():
    import inspect

    from app.analytics.router import ExportBody, export_download

    for format in ("json", "csv", "pdf", "xlsx"):
        assert ExportBody(format=format).scope == "summary"
    assert not inspect.iscoroutinefunction(export_download)


@pytest.mark.parametrize("format", ["pdf", "xlsx"])
def test_binary_download_renders_between_distinct_transactions(monkeypatch, format):
    from contextlib import contextmanager

    from app.analytics import service
    from app.common.errors import DomainError

    calls, opened = [], []
    active = False
    binding = "captured"

    @contextmanager
    def begin():
        nonlocal active
        assert not active
        active = True
        session = object()
        opened.append(session)
        calls.append("begin")
        try:
            yield session
        finally:
            calls.append("end")
            active = False

    def capture(*args):
        assert active
        calls.append("authorize")
        return service.ExportCapture(format, b'{"original":"data"}', binding)

    def render(*args):
        assert not active
        calls.append("render")
        return b"document"

    monkeypatch.setattr(service, "capture_export", capture)
    monkeypatch.setattr(service, "generate_document", render)
    sessions = SimpleNamespace(begin=begin)
    assert service.download_export(sessions, uuid4(), uuid4(), uuid4())[0] == b"document"
    assert calls == ["begin", "authorize", "end", "render", "begin", "authorize", "end"]
    assert opened[0] is not opened[1]

    def revoke(*args):
        nonlocal binding
        assert not active
        binding = "changed-privacy-epoch"
        return b"must not escape"

    monkeypatch.setattr(service, "generate_document", revoke)
    with pytest.raises(DomainError) as error:
        service.download_export(sessions, uuid4(), uuid4(), uuid4())
    assert error.value.code == "ANALYSIS_UNAVAILABLE"


@pytest.mark.parametrize("format", ["json", "csv", "pdf", "xlsx"])
def test_download_response_mime_filename_and_privacy_headers(monkeypatch, format):
    from app.analytics import router as module
    from app.analytics.exports import MEDIA_TYPES

    monkeypatch.setattr(module, "guard", lambda *args: None)
    sessions = object()  # The route must pass the factory, not begin a transaction.

    def download(factory, *args):
        assert factory is sessions
        return b"content", MEDIA_TYPES[format]

    monkeypatch.setattr(module.service, "download_export", download)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(database=SimpleNamespace(sessions=sessions)))
    )
    response = module.export_download(uuid4(), uuid4(), request, None, SimpleNamespace(id=uuid4()))
    assert response.body == b"content"
    assert response.headers["content-type"].split(";")[0] == MEDIA_TYPES[format]
    assert response.headers["content-disposition"] == f'attachment; filename="report.{format}"'
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_missing_font_is_actionable_and_no_sensitive_diagnostics_escape(monkeypatch):
    from app.analytics import exports
    from app.common.errors import DomainError

    monkeypatch.setenv("REPORT_EXPORT_FONT", "/font-that-does-not-exist.ttf")
    with pytest.raises(DomainError) as error:
        exports.generate_document({"participant": "private content"}, "pdf")
    assert error.value.code == "EXPORT_FONT_UNAVAILABLE"
    assert "private content" not in error.value.message
    assert "font-that-does-not-exist" not in error.value.message


def test_concurrent_render_limit_fails_fast_and_is_retryable(monkeypatch):
    from app.analytics import exports
    from app.common.errors import DomainError

    exports._SLOTS.acquire()
    exports._SLOTS.acquire()
    try:
        with pytest.raises(DomainError) as error:
            exports.generate_document({}, "xlsx")
        assert error.value.code == "EXPORT_BUSY"
    finally:
        exports._SLOTS.release()
        exports._SLOTS.release()
    assert exports.generate_document({}, "xlsx").startswith(b"PK")
