"""Pure deterministic reducers. One final answer per session/block, never per revision."""

import csv
import hashlib
import io
import json
from collections import Counter
from statistics import median

VERSION = "p09.1"
MIN_GROUP = 5


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def metric(numerator, denominator, exclusions, **extra):
    return dict(
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator if denominator else None,
        source_unit="session",
        exclusions=exclusions,
        metric_version=VERSION,
        **extra,
    )


def reduce_block(block, answers, population_exclusions=None):
    counts = Counter(a["status"] for a in answers)
    valid = [a["value"] for a in answers if a["status"] == "responded"]
    exclusions = dict(population_exclusions or {}) | {
        k: counts[k] for k in ("missing", "skipped", "unable")
    }
    result = {
        "type": block.type,
        "missingness": metric(
            len(answers) - len(valid), len(answers), dict(population_exclusions or {})
        ),
        "response": metric(len(valid), len(answers), exclusions),
    }
    if block.type in {"survey.single", "survey.multi"}:
        choices = Counter(
            k
            for v in valid
            for k in ([v["option_id"]] if block.type == "survey.single" else set(v["option_ids"]))
        )
        result["distribution"] = {
            o.id: metric(choices[o.id], len(valid), exclusions) for o in block.config.options
        }
    elif block.type == "survey.rating":
        values = [v["value"] for v in valid]
        result["distribution"] = {
            str(k): metric(values.count(k), len(values), exclusions)
            for k in range(block.config.min, block.config.max + 1, block.config.step)
        }
        result["median"] = metric(
            len(values), len(valid), exclusions, statistic=median(values) if values else None
        )
        result["median"].update(
            value=median(values) if values else None, aggregation="median", sample_n=len(values)
        )
    elif block.type == "preference":
        choices = Counter(v.get("selected_variant_id") or v["decision"] for v in valid)
        keys = [v.id for v in block.config.variants] + ["tie", "none"]
        result["distribution"] = {k: metric(choices[k], len(valid), exclusions) for k in keys}
    elif block.type == "prototype.task":
        times = [v["elapsed_ms"] for v in valid if v["outcome"] == "completed"]
        result["completion"] = metric(
            len(times),
            len(answers),
            dict(population_exclusions or {}),
            provenance="self_report",
            population="all_included_sessions",
        )
        result["time_on_task"] = metric(
            len(times),
            len(valid),
            exclusions,
            statistic=median(times) if times else None,
            unit="ms",
            provenance="self_report",
            population="completed_tasks",
        )
        result["time_on_task"].update(
            value=median(times) if times else None, aggregation="median", sample_n=len(times)
        )
    elif block.type == "five_second":
        timing_valid = sum(not v["interrupted"] and 4900 <= v["visible_ms"] <= 5250 for v in valid)
        result["timing_valid"] = metric(
            timing_valid, len(valid), exclusions, provenance="client_observed_not_verified_exposure"
        )
    from app.studies import advanced

    result.update(advanced.reduce(block, valid, len(answers), metric, exclusions))
    return result


def safe_cell(value):
    value = str(value)
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n"))
        or value.startswith(("\t", "\r", "\n"))
        else value
    )


def csv_document(data):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(["path", "value"])

    def walk(value, path):
        if isinstance(value, dict):
            for key in sorted(value):
                walk(value[key], path + [str(key)])
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path + [str(i)])
        else:
            writer.writerow([safe_cell("/".join(path)), safe_cell("" if value is None else value)])

    walk(data, [])
    return out.getvalue()


def compare_metrics(left, right, left_count, right_count):
    # Suppress entire complementary partition, not just the tiny cell.
    if min(left_count, right_count) < MIN_GROUP:
        return {
            "suppressed": True,
            "reason": "small_or_complementary_group",
            "metric_version": VERSION,
        }
    differences = {}

    def walk(a, b, path):
        if isinstance(a, dict) and isinstance(b, dict):
            if "numerator" in a and "denominator" in a:
                differences["/".join(path)] = (
                    None if a["value"] is None or b["value"] is None else b["value"] - a["value"]
                )
            else:
                for k in sorted(a.keys() & b.keys()):
                    walk(a[k], b[k], path + [k])

    walk(left, right, [])
    return {
        "suppressed": False,
        "interpretation": "descriptive_only_not_causal",
        "differences": differences,
        "metric_version": VERSION,
    }


def redacted_metrics(data):
    """Suppress an entire distribution when a small/complementary cell exists.

    Zero cells are non-sensitive; missingness is protected like other metrics.
    No aggregate labels or text payloads are copied outside this typed structure.
    """

    def small(m):
        return m.get("denominator", 0) < MIN_GROUP or any(
            0 < n < MIN_GROUP
            for n in (m.get("numerator", 0), m.get("denominator", 0) - m.get("numerator", 0))
        )

    def walk(value):
        if not isinstance(value, dict):
            return value
        if "numerator" in value and "denominator" in value:
            if small(value):
                return {"suppressed": True, "metric_version": VERSION, "source_unit": "session"}
            # Exclusion counts may identify tiny cells independently of denominator.
            return {k: walk(v) for k, v in value.items() if k != "exclusions"} | {
                "exclusions": "redacted"
            }
        result = {}
        for key, item in value.items():
            if key == "distribution" and any(small(m) for m in item.values()):
                result[key] = {"suppressed": True, "metric_version": VERSION}
            elif key in {"included", "excluded"}:
                continue
            else:
                result[key] = walk(item)
        return result

    return walk(data)
