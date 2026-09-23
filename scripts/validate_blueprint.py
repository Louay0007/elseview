#!/usr/bin/env python3
"""Validate blueprint documents, not a running backend. Standard library only."""

import argparse
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    ROOT / "BACKEND_BLUEPRINT.md",
    ROOT / "docs/backend/DATA_MODEL.md",
    ROOT / "docs/backend/RESEARCH_METHODS.md",
    ROOT / "docs/backend/AI_CLOUD.md",
    ROOT / "docs/backend/SELF_HOSTING.md",
    ROOT / "docs/backend/FEATURE_CONTRACTS.md",
    ROOT / "BACKEND_IMPLEMENTATION_PLAN.md",
    ROOT / "docs/backend/MODEL_TEST_MATRIX.md",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^\s)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})([^\s]*)\s*$")


def split_document(text):
    """Return prose, fenced examples and structural errors."""
    prose, examples, errors = [], [], []
    active = None
    contents = []
    for line_number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if active is None:
            if match:
                active = (match.group(1), match.group(2), line_number)
                contents = []
            else:
                prose.append(line)
        elif match and match.group(1)[0] == active[0][0] and len(match.group(1)) >= len(active[0]) and not match.group(2):
            examples.append((active[1], "\n".join(contents), active[2]))
            active = None
        else:
            contents.append(line)
    if active:
        errors.append("Unclosed code fence at line %s" % active[2])
    return "\n".join(prose), examples, errors


def anchors(text):
    prose, _, _ = split_document(text)
    counts, result = {}, set()
    for line in prose.splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        value = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
        number = counts.get(value, 0)
        counts[value] = number + 1
        result.add(value if number == 0 else "%s-%s" % (value, number))
    return result


def validate_document(path):
    errors = []
    if not path.is_file():
        return ["Missing document: %s" % path], 0
    text = path.read_text(encoding="utf-8")
    prose, examples, fence_errors = split_document(text)
    errors.extend(fence_errors)
    if not text.startswith("# "):
        errors.append("Missing top-level title")
    if "\ufffd" in text:
        errors.append("Contains a Unicode replacement character")
    if re.search(r"\b(?:TODO|FIXME|TBD)\b|\[USER_ADDED:", text):
        errors.append("Contains an unresolved drafting marker")
    parsed_json = 0
    for language, example, line in examples:
        if language.lower() == "json":
            try:
                json.loads(example)
                parsed_json += 1
            except json.JSONDecodeError as exc:
                errors.append("Invalid JSON at fence line %s: %s" % (line, exc))
    for target in LINK.findall(prose):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue  # Online link availability is not checked by this script.
        destination = path if not parsed.path else Path(unquote(parsed.path))
        if not destination.is_absolute():
            destination = path.parent / destination
        destination = destination.resolve()
        if not destination.is_file():
            errors.append("Broken local file reference: %s" % target)
        elif parsed.fragment and destination.suffix.lower() == ".md":
            if unquote(parsed.fragment) not in anchors(destination.read_text(encoding="utf-8")):
                errors.append("Broken local heading reference: %s" % target)
    return errors, parsed_json


class ValidatorTests(unittest.TestCase):
    def test_headings_ignore_code_and_suffix_duplicates(self):
        self.assertEqual(anchors("# Title\n## A\n## A\n```text\n## Hidden\n```\n"), {"title", "a", "a-1"})

    def test_unclosed_fence_is_error(self):
        self.assertTrue(split_document("# Title\n```json\n{}")[2])

    def test_good_document_and_local_link(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "doc.md"
            path.write_text('# Title\n[Jump](#example)\n## Example\n```json\n{"ok": true}\n```\n', encoding="utf-8")
            self.assertEqual(validate_document(path), ([], 1))

    def test_bad_json_and_link_are_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "doc.md"
            path.write_text('# Title\n[Missing](missing.md)\n```json\n{"ok": }\n```\n', encoding="utf-8")
            errors, count = validate_document(path)
            self.assertEqual(count, 0)
            self.assertEqual(len(errors), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run validator unit tests only")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ValidatorTests))
        return 0 if result.wasSuccessful() else 1
    failures, json_count = [], 0
    for path in DOCUMENTS:
        errors, count = validate_document(path)
        json_count += count
        failures.extend("%s: %s" % (path, error) for error in errors)
        print("%s %s (%s JSON examples)" % ("FAIL" if errors else "PASS", path, count))
    if DOCUMENTS[0].is_file():
        main_text = DOCUMENTS[0].read_text(encoding="utf-8")
        sections = [int(value) for value in re.findall(r"^## (\d+)\. ", main_text, re.M)]
        if sections != list(range(1, 14)):
            failures.append("Main blueprint must contain sections 1–13 exactly once, in order")
        for phrase in ("diary", "accessibility", "private-panel", "consent", "compensation", "idempotent", "cloud", "PostgreSQL", "FastAPI"):
            if phrase.lower() not in main_text.lower():
                failures.append("Missing feature coverage: %s" % phrase)
    plan_path = ROOT / "BACKEND_IMPLEMENTATION_PLAN.md"
    matrix_path = ROOT / "docs/backend/MODEL_TEST_MATRIX.md"
    if plan_path.is_file() and matrix_path.is_file():
        plan = plan_path.read_text(encoding="utf-8")
        matrix = matrix_path.read_text(encoding="utf-8")
        phases = re.findall(r"^## \d+\. (P\d{2}) —", plan, re.M)
        if phases != ["P%02d" % number for number in range(1, 20)]:
            failures.append("Implementation plan must contain P01–P19 exactly once, in order")
        dictionary = (ROOT / "docs/backend/DATA_MODEL.md").read_text(encoding="utf-8")
        models = re.findall(r"^#### \d+\. `([^`]+)`", dictionary, re.M)
        mapped = re.findall(r"^\| `([^`]+)` \| P", matrix, re.M)
        if sorted(models) != sorted(mapped):
            failures.append("Model matrix must map every extended dictionary model exactly once")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Validated %s blueprint documents and %s JSON examples. Runtime behavior was NOT tested." % (len(DOCUMENTS), json_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())