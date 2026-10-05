"""Conditional event-time intervals from synthetic declarations, never causation."""
import argparse
import hashlib
import itertools
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bounded_io as bio

MODEL = "conservative-closed-event-time/v1"
MAX_SOURCES = 8
MAX_EVENTS = 32
MAX_PAIRS = 496
MAX_ERROR = 86400000000
QUANTA = (1, 10, 100, 1000, 10000, 100000, 1000000)
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
TIMESTAMP = re.compile(r"(?P<digits>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)(?P<suffix>Z|[+-]\d{2}:\d{2})?\Z", re.ASCII)
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
END = datetime(2100, 1, 1, tzinfo=timezone.utc)
MAX_TIME = ((END - EPOCH).days * 86400) * 1000000 - 1


def _identity(value):
    if type(value) is not str or not ID.fullmatch(value):
        raise bio.InputError("invalid source/event ID")


def _integer(value):
    if type(value) is not int:
        raise bio.InputError("integer required; booleans are not integers in this schema")


def _range(value):
    if not 0 <= value <= MAX_TIME:
        raise bio.InputError("normalized or interval endpoint outside 2000–2099")


def iso(value):
    return (EPOCH + timedelta(microseconds=value)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_timestamp(value):
    """Return logged UTC microseconds or None, local fraction, and offset context."""
    if type(value) is not str or not (match := TIMESTAMP.fullmatch(value)):
        raise bio.InputError("unsupported timestamp syntax")
    try:
        local = datetime.fromisoformat(match["digits"])
    except ValueError as exc:
        raise bio.InputError("invalid calendar timestamp or unsupported leap second") from exc
    if not 2000 <= local.year <= 2099:
        raise bio.InputError("local timestamp outside 2000–2099")
    suffix = match["suffix"]
    if suffix is None:
        return None, local.microsecond, "missing_utc_context"
    minutes = 0
    context = "original_local_offset_unknown"
    if suffix != "Z":
        hours, remainder = int(suffix[1:3]), int(suffix[4:6])
        if hours > 23 or remainder > 59:
            raise bio.InputError("invalid numeric timezone offset")
        minutes = (hours * 60 + remainder) * (-1 if suffix[0] == "-" else 1)
        if suffix != "-00:00":
            context = "numeric_local_offset_declared"
    utc = local.replace(tzinfo=timezone(timedelta(minutes=minutes))).astimezone(timezone.utc)
    elapsed = utc - EPOCH
    micros = (elapsed.days * 86400 + elapsed.seconds) * 1000000 + elapsed.microseconds
    _range(micros)
    return micros, local.microsecond, context


def _quantization(value, fraction):
    if value is None:
        return
    bio.fields(value, ("mode", "quantum_us"))
    if type(value["mode"]) is not str or value["mode"] not in ("truncated", "rounded"):
        raise bio.InputError("unsupported quantization mode")
    _integer(value["quantum_us"])
    if value["quantum_us"] not in QUANTA:
        raise bio.InputError("unsupported quantum")
    if fraction % value["quantum_us"]:
        raise bio.InputError("timestamp contradicts quantization alignment")


def _error(value):
    if value is None:
        return
    bio.fields(value, ("min", "max"))
    for bound in value.values():
        _integer(bound)
        if not -MAX_ERROR <= bound <= MAX_ERROR:
            raise bio.InputError("clock-error bound exceeded")
    if value["min"] > value["max"]:
        raise bio.InputError("clock-error endpoints reversed")


def validate(raw):
    """Validate the entire scenario, including assumptions on unknown-context rows."""
    data = bio.decode(raw)
    bio.fields(data, ("schema_version", "source_kind", "label", "sources", "events"))
    _integer(data["schema_version"])
    if data["schema_version"] != 1 or data["source_kind"] != "synthetic":
        raise bio.InputError("unsupported schema version or source kind")
    if type(data["label"]) is not str or not bio.visible(data["label"]).strip():
        raise bio.InputError("nonempty neutral label required")
    sources, events = data["sources"], data["events"]
    if type(sources) is not list or len(sources) > MAX_SOURCES:
        raise bio.InputError("source count limit exceeded or invalid list")
    seen = set()
    for source in sources:
        _identity(source)
        if source in seen:
            raise bio.InputError("duplicate source ID")
        seen.add(source)
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise bio.InputError("event count limit exceeded or invalid list")
    seen_events = set()
    for event in events:
        bio.fields(event, ("event_id", "source_id", "original_timestamp", "timestamp_role", "quantization", "clock_error_us"))
        _identity(event["event_id"])
        _identity(event["source_id"])
        if event["event_id"] in seen_events:
            raise bio.InputError("duplicate event ID")
        seen_events.add(event["event_id"])
        if event["source_id"] not in seen:
            raise bio.InputError("dangling source reference")
        if type(event["timestamp_role"]) is not str or event["timestamp_role"] not in ("event_time", "ingest_time", "unknown"):
            raise bio.InputError("unsupported timestamp role")
        _logged, fraction, _context = parse_timestamp(event["original_timestamp"])
        # Do not let missing offset/role/other assumptions bypass supplied validation.
        _quantization(event["quantization"], fraction)
        _error(event["clock_error_us"])
        event_interval(event)  # Reject expanded endpoints before any scenario output.
    return data


def event_interval(event):
    """Pure conservative envelope for one already schema-validated event."""
    logged, _fraction, offset_context = parse_timestamp(event["original_timestamp"])
    quantum = event["quantization"]
    error = event["clock_error_us"]
    reasons = []
    if logged is None:
        reasons.append("utc_context_missing")
    if event["timestamp_role"] != "event_time":
        reasons.append("event_occurrence_role_not_established")
    if quantum is None:
        reasons.append("quantization_unknown")
    if error is None:
        reasons.append("clock_error_unknown")
    interval = None
    if not reasons:
        q = quantum["quantum_us"]
        if quantum["mode"] == "truncated":
            logged_lower, logged_upper = logged, logged + q
        else:
            half = (q + 1) // 2
            logged_lower, logged_upper = logged - half, logged + half
        lower = logged_lower - error["max"]
        upper = logged_upper - error["min"]
        _range(lower)
        _range(upper)
        interval = {"lower_us": lower, "upper_us": upper, "lower_utc": iso(lower), "upper_utc": iso(upper)}
    return {"event_id": event["event_id"], "source_id": event["source_id"],
            "original_timestamp": event["original_timestamp"], "timestamp_role": event["timestamp_role"],
            "quantization": dict(quantum) if quantum is not None else None,
            "clock_error_us": dict(error) if error is not None else None,
            "logged_utc": iso(logged) if logged is not None else None,
            "offset_context": offset_context, "status": "unknown_context" if reasons else "conditional_interval",
            "unknown_reasons": reasons, "interval": interval}


def compare(a, b):
    """Conditional strict order; equality/touch/overlap never assert simultaneity."""
    left, right = a["interval"], b["interval"]
    if left is None or right is None:
        relation, reason = "unknown_context", "At least one event lacks a complete conditional interval."
    elif left["upper_us"] < right["lower_us"]:
        relation, reason = "guaranteed_before", "A upper endpoint is strictly below B lower endpoint under supplied assumptions."
    elif right["upper_us"] < left["lower_us"]:
        relation, reason = "guaranteed_after", "B upper endpoint is strictly below A lower endpoint under supplied assumptions."
    else:
        relation, reason = "order_not_established", "Closed envelopes overlap or touch; neither strict order nor simultaneity is established."
    return {"a": a["event_id"], "b": b["event_id"], "relation": relation, "reason": reason,
            "a_interval": left, "b_interval": right}


def evaluate(data, digest):
    """Pure report from validated data; ID order is presentation, never event order."""
    rows = [event_interval(event) for event in sorted(data["events"], key=lambda e: e["event_id"])]
    pairs = [compare(a, b) for a, b in itertools.combinations(rows, 2)]
    if len(pairs) > MAX_PAIRS:
        raise bio.InputError("pair count limit exceeded")
    return {"report_version": 1, "model": MODEL, "source_kind": "synthetic", "label": data["label"],
            "input_sha256": digest, "sources": sorted(data["sources"]), "events": rows, "pairs": pairs,
            "counts": {"events": len(rows), "pairs": len(pairs), "unknown_events": sum(row["interval"] is None for row in rows)},
            "causation": "not_established", "assumptions": [
                "All envelopes and guaranteed relations are conditional on unverified supplied synthetic assertions.",
                "Clock error is logged minus true UTC; subtract error max from lower and error min from upper.",
                "Quantization envelopes are conservative and closed, including the truncated upper boundary.",
                "Rounded half quanta expand outward to integer microseconds.",
                "No shared-source clock cancellation, continuity, ingestion-delay correction or simultaneity inference.",
                "IDs sort presentation only; overlapping intervals are not transitive equivalence classes.",
                "Hash identifies bytes, not authenticity, real-clock accuracy or event truth."],
            "limits": {"input_bytes": bio.MAX_BYTES, "depth": bio.MAX_DEPTH, "numeric_token_chars": bio.MAX_NUMBER,
                       "string_chars": bio.MAX_STRING, "sources": MAX_SOURCES, "events": MAX_EVENTS,
                       "pairs": MAX_PAIRS, "output_bytes": bio.MAX_OUTPUT}}


def render(report, format_name):
    if format_name == "json":
        text = json.dumps(report, ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2) + "\n"
    elif format_name == "markdown":
        lines = ["# Conditional event-time comparison", "", "Causation: **not established**. ID order is presentation only.", "",
                 "Label: " + bio.markdown(report["label"]), "Model: " + bio.markdown(report["model"]),
                 "Input SHA-256: " + bio.markdown(report["input_sha256"]), "", "## Events", ""]
        for event in report["events"]:
            # A code block encodes every JSON string; backticks in IDs/times are forbidden.
            lines.extend(["```json", json.dumps(event, ensure_ascii=True, sort_keys=True), "```", ""])
        lines.extend(["## Complete pair relations", "", "| A | B | Conditional relation | Reason |", "|---|---|---|---|"])
        for pair in report["pairs"]:
            lines.append("| " + " | ".join(bio.markdown(pair[key]) for key in ("a", "b", "relation", "reason")) + " |")
        lines.extend(["", "Assumptions and limitations:", "", *("- " + line for line in report["assumptions"]), "", "Limits:", "", *(f"- {key}: {value}" for key, value in report["limits"].items())])
        text = "\n".join(lines) + "\n"
    else:
        raise bio.InputError("unsupported output format")
    raw = text.encode("utf-8")
    if len(raw) > bio.MAX_OUTPUT:
        raise bio.InputError("output byte limit exceeded")
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="new report only, never overwrite")
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as handle:
            raw = handle.read(bio.MAX_BYTES + 1)
        data = validate(raw)
        result = render(evaluate(data, hashlib.sha256(raw).hexdigest()), args.format)
        if args.output:
            bio.write_new(args.output, result, input_path=args.input)
        else:
            text = result.decode("utf-8")
            if sys.stdout.write(text) != len(text):
                raise OSError("short stdout write")
            sys.stdout.flush()
        return 0
    except UnicodeError:
        print("Rejected: output encoding failure", file=sys.stderr)
        return 2
    except bio.OutputCleanupError as exc:
        print("Complete report published; temporary cleanup failed." if exc.published else "Report not published; temporary cleanup failed.", file=sys.stderr)
        return 3 if exc.published else 2
    except (bio.InputError, OSError) as exc:
        print("Rejected: " + (str(exc) if isinstance(exc, bio.InputError) else type(exc).__name__), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
