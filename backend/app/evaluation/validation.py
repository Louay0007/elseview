import hashlib
import json
import math
import re
import unicodedata

from app.studies.advanced import contains, intersects, polygon_valid


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def content_identity(source):
    # Deliberately excludes caller UUID/key, model settings, language and candidates.
    # Same prompt/source cannot cross partitions even after changing candidate outputs.
    return digest(
        {
            "text": None
            if source.get("asset_checksum")
            else unicodedata.normalize("NFKC", source["text"]).strip(),
            "image": source.get("asset_checksum"),
        }
    )


def validate_outcome(schema, source, body):
    task = schema["task"]
    a = body.annotations
    if task in {"classification", "text_spans", "image_polygons"}:
        if body.choice is not None or body.ratings or body.turns or body.outcome:
            raise ValueError("Unexpected outcome fields")
        if not schema["min_annotations"] <= len(a) <= schema["max_annotations"]:
            raise ValueError("Annotation count")
        known = {v["id"] for v in schema["labels"]}
        seen = set()
        for v in a:
            if v.label_id not in known:
                raise ValueError("Unknown label")
            if task == "classification":
                if (
                    v.label_id in seen
                    or v.start is not None
                    or v.end is not None
                    or v.polygon is not None
                ):
                    raise ValueError("Invalid class")
                seen.add(v.label_id)
            if task == "text_spans":
                if (
                    v.polygon is not None
                    or v.start is None
                    or v.end is None
                    or not 0 <= v.start < v.end <= len(source["text"])
                ):
                    raise ValueError("Invalid Unicode span")
            if task == "image_polygons":
                if (
                    v.start is not None
                    or v.end is not None
                    or not v.polygon
                    or any(not math.isfinite(c) or not 0 <= c <= 1 for p in v.polygon for c in p)
                ):
                    raise ValueError("Invalid polygon")
                polygon_valid(v.polygon)
        if not schema["allow_overlap"]:
            for i, left in enumerate(a):
                for right in a[i + 1 :]:
                    if task == "text_spans" and max(left.start, right.start) < min(
                        left.end, right.end
                    ):
                        raise ValueError("Overlapping spans")
                    if task == "image_polygons":
                        p, q = left.polygon, right.polygon
                        if (
                            contains(p, q[0])
                            or contains(q, p[0])
                            or any(
                                intersects(x, p[(j + 1) % len(p)], y, q[(k + 1) % len(q)])
                                for j, x in enumerate(p)
                                for k, y in enumerate(q)
                            )
                        ):
                            raise ValueError("Overlapping polygons")
    elif task in {"pairwise", "language_review"}:
        if a or body.turns or body.outcome:
            raise ValueError("Unexpected outcome fields")
        if task == "pairwise" and body.choice is None:
            raise ValueError("Choice required")
        if task == "language_review" and body.choice is not None:
            raise ValueError("Unexpected choice")
        dimensions = {v["id"]: v for v in schema["dimensions"]}
        candidates = ["left", "right"] if task == "pairwise" else ["source"]
        expected = {(c, d) for c in candidates for d in dimensions}
        if body.choice == "cannot_judge":
            expected = set()
        actual = {(r.candidate_id, r.dimension_id) for r in body.ratings}
        if actual != expected or len(actual) != len(body.ratings):
            raise ValueError("Incomplete or repeated ratings")
        for r in body.ratings:
            if (
                not dimensions[r.dimension_id]["min"]
                <= r.value
                <= dimensions[r.dimension_id]["max"]
            ):
                raise ValueError("Rating bounds")
    else:
        s = source["scenario"]
        if (
            a
            or body.choice
            or body.ratings
            or not body.outcome
            or not body.fictional_confirmation
            or body.scenario_revision != s["revision"]
        ):
            raise ValueError("Scenario mismatch")
        if (
            body.duration_ms is None
            or body.duration_ms > s["max_duration_ms"]
            or not 1 <= len(body.turns) <= s["max_turns"]
            or sum(len(t.text) for t in body.turns) > s["max_characters"]
        ):
            raise ValueError("Transcript bounds")
        # Defense in depth, not a claim to detect all personal data. Manual fictional attestation required.
        text = " ".join(t.text for t in body.turns) + " " + body.reason.text
        if re.search(
            r"https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b\d{7,}\b|\b(?:password|api[_ -]?key|bearer)\s*[:=]",
            text,
            re.I,
        ):
            raise ValueError("Potential private data or live destination")
