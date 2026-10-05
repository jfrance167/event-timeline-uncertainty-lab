"""Original synthetic hand-calculated interval and trust-boundary checks."""
import contextlib
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bounded_io as bio
import timeline as lab

ROOT = Path(__file__).resolve().parents[1]
T = 129600000000  # Jan 2, 2000 at 12:00 UTC: 1.5 days from Jan 1, integer us.


def event(identity="A", timestamp="2000-01-02T12:00:00Z", *, q=1000000, error=None):
    return {"event_id": identity, "source_id": "lab", "original_timestamp": timestamp,
            "timestamp_role": "event_time", "quantization": {"mode": "truncated", "quantum_us": q},
            "clock_error_us": error if error is not None else {"min": 0, "max": 0}}


def scenario(*events):
    return {"schema_version": 1, "source_kind": "synthetic", "label": "Synthetic time bounds",
            "sources": ["lab"], "events": list(events) or [event()]}


def raw(data):
    return json.dumps(data).encode()


def analyze(data):
    encoded = raw(data)
    return lab.evaluate(lab.validate(encoded), hashlib.sha256(encoded).hexdigest())


class ContractTests(unittest.TestCase):
    def reject(self, data):
        with self.assertRaises(bio.InputError):
            lab.validate(raw(data))

    def test_version_strict(self):
        for value in (True, 1.0, "1", 2, None):
            data = scenario()
            data["schema_version"] = value
            with self.subTest(value=value):
                self.reject(data)

    def test_root_fields_source_kind_and_label(self):
        for key, value in (("source_kind", "sanitized"), ("label", "\x1b\u202e"), ("label", None)):
            data = scenario()
            data[key] = value
            self.reject(data)
        data = scenario()
        data["hostname"] = "private"
        self.reject(data)
        del data["hostname"]
        del data["sources"]
        self.reject(data)

    def test_sources_identity_and_count(self):
        for value in (["lab", "lab"], ["bad|id"], ["x"] * 9, [1], "lab", None, ["a" * 65], ["\u0430"]):
            data = scenario()
            data["sources"] = value
            self.reject(data)

    def test_event_duplicate_reference_fields_and_id(self):
        self.reject(scenario(event(), event()))
        for key, value in (("event_id", "<script>"), ("source_id", "dangling"), ("timestamp_role", "collected"), ("timestamp_role", None)):
            row = event()
            row[key] = value
            self.reject(scenario(row))
        row = event()
        del row["clock_error_us"]
        self.reject(scenario(row))

    def test_event_count_and_list_type(self):
        data = scenario()
        for value in ([event()] * 33, None, {}):
            data["events"] = value
            self.reject(data)

    def test_duplicate_json_fields_and_canonical_escape(self):
        for encoded in (b'{"a":1,"a":2}', br'{"a":1,"\u0061":2}', b'{"outer":{"a":1,"a":2}}'):
            with self.assertRaises(bio.InputError):
                lab.validate(encoded)

    def test_float_nonfinite_and_numeric_token(self):
        for value in ("1.0", "1e1", "NaN", "Infinity", "-Infinity", "1" * 21):
            with self.subTest(value=value), self.assertRaises(bio.InputError):
                lab.validate(('{"schema_version":' + value + '}').encode())

    def test_bytes_nesting_and_malformed_utf8_json(self):
        for encoded in (b" " * 65537, b"[" * 13 + b"0" + b"]" * 13, b"\xff", b"\xef\xbb\xbf{}", b"{", b"{} {}", b"null", b'{"x":"\x01"}'):
            with self.subTest(length=len(encoded)), self.assertRaises(bio.InputError):
                lab.validate(encoded)

    def test_string_limits_surrogates_and_quoted_scanner(self):
        data = scenario()
        for value in ("a" * 257, "\ud800"):
            data["label"] = value
            self.reject(data)
        data["label"] = "[" * 20 + "9" * 40 + '\\"' + "]" * 20
        self.assertEqual(lab.validate(raw(data))["label"], data["label"])

    def test_unsupported_timestamp_forms(self):
        for value in ("2000-01-02", "2000-01-02T12:00:60Z", "2000-02-30T12:00:00Z", "2000-01-02T12:00:00.1234567Z", "2000-01-02T12:00:00+00:60", "2000-01-02T12:00:00-01:99", "2000-01-02T12:00:00+24:00", "2000-01-02T12:00:00Z[Europe/Paris]", "946771200", None, "２０００-01-02T12:00:00Z"):
            with self.subTest(value=value):
                self.reject(scenario(event(timestamp=value)))

    def test_quantum_alignment_modes_and_true_integer(self):
        self.reject(scenario(event(timestamp="2000-01-02T12:00:00.1Z")))
        for value in ({"mode": "guess", "quantum_us": 1}, {"mode": "rounded", "quantum_us": True}, {"mode": "truncated", "quantum_us": 3}, {}, 1):
            row = event()
            row["quantization"] = value
            self.reject(scenario(row))

    def test_error_bounds_and_types(self):
        for value in ({"min": 2, "max": 1}, {"min": True, "max": 1}, {"min": -86400000001, "max": 0}, {"min": 0, "max": 86400000001}, {}, 1):
            row = event()
            row["clock_error_us"] = value
            self.reject(scenario(row))

    def test_unknown_context_cannot_bypass_provided_validation(self):
        cases = []
        row = event(timestamp="2000-01-02T12:00:00")
        row["clock_error_us"] = {"min": 2, "max": 1}
        cases.append(row)
        row = event(timestamp="2000-01-02T12:00:00.1")
        row["clock_error_us"] = None
        cases.append(row)  # invalid provided quantum alignment despite two unknowns
        row = event()
        row["timestamp_role"] = "ingest_time"
        row["quantization"] = {"mode": "guessed", "quantum_us": 1}
        cases.append(row)
        row = event(timestamp="2000-01-02T12:00:00+00:60")
        row["quantization"] = row["clock_error_us"] = None
        cases.append(row)
        for row in cases:
            self.reject(scenario(row))

    def test_local_normalized_and_expanded_range(self):
        for value in ("1999-12-31T23:59:59Z", "2100-01-01T00:00:00Z", "2000-01-01T00:00:00+00:01", "2099-12-31T23:59:59-00:01"):
            self.reject(scenario(event(timestamp=value)))
        row = event(timestamp="2000-01-01T00:00:00Z", error={"min": 1, "max": 2})
        self.reject(scenario(row))
        self.reject(scenario(event(timestamp="2099-12-31T23:59:59Z")))

    def test_empty_scenario_and_case_sensitive_ids(self):
        data = scenario()
        data["events"] = data["sources"] = []
        self.assertEqual(analyze(data)["counts"], {"events": 0, "pairs": 0, "unknown_events": 0})
        data = scenario(event("a"), event("A"))
        data["sources"] = ["lab", "LAB"]
        self.assertEqual([row["event_id"] for row in analyze(data)["events"]], ["A", "a"])


class ModelTests(unittest.TestCase):
    def bounds(self, row):
        result = analyze(scenario(row))["events"][0]["interval"]
        return result["lower_us"], result["upper_us"]

    def test_hand_calculated_positive_error(self):
        self.assertEqual(self.bounds(event(error={"min": 2000000, "max": 3000000})), (T - 3000000, T - 1000000))

    def test_hand_calculated_negative_and_mixed_error(self):
        self.assertEqual(self.bounds(event(error={"min": -3000000, "max": -2000000})), (T + 2000000, T + 4000000))
        self.assertEqual(self.bounds(event(error={"min": -1000000, "max": 2000000})), (T - 2000000, T + 2000000))

    def test_rounded_quantization_half_and_odd_outward(self):
        row = event(q=1000000)
        row["quantization"]["mode"] = "rounded"
        self.assertEqual(self.bounds(row), (T - 500000, T + 500000))
        row["quantization"]["quantum_us"] = 1
        self.assertEqual(self.bounds(row), (T - 1, T + 1))

    def test_truncated_closed_upper_and_touch(self):
        a, b = event(), event("B", "2000-01-02T12:00:01Z")
        self.assertEqual(self.bounds(a), (T, T + 1000000))
        self.assertEqual(analyze(scenario(a, b))["pairs"][0]["relation"], "order_not_established")

    def test_strict_before_and_after(self):
        result = analyze(scenario(event(), event("B", "2000-01-02T12:00:01.000001Z", q=1)))
        self.assertEqual(result["pairs"][0]["relation"], "guaranteed_before")
        result = analyze(scenario(event("A", "2000-01-02T12:00:03Z"), event("B")))
        self.assertEqual(result["pairs"][0]["relation"], "guaranteed_after")

    def test_overlap_not_transitive(self):
        # Hand envelopes: A [0,1]s, B [.8,1.8]s, C [1.6,2.6]s relative to T.
        rows = [event("A", q=100000, error={"min": -900000, "max": 0}),
                event("B", "2000-01-02T12:00:00.8Z", q=100000, error={"min": -900000, "max": 0}),
                event("C", "2000-01-02T12:00:01.6Z", q=100000, error={"min": -900000, "max": 0})]
        relations = {(p["a"], p["b"]): p["relation"] for p in analyze(scenario(*rows))["pairs"]}
        self.assertEqual(relations, {("A", "B"): "order_not_established", ("A", "C"): "guaranteed_before", ("B", "C"): "order_not_established"})

    def test_equal_and_contained_no_simultaneity(self):
        result = analyze(scenario(event(), event("B")))
        self.assertEqual(result["pairs"][0]["relation"], "order_not_established")
        result = analyze(scenario(event(), event("B", "2000-01-02T12:00:00.5Z", q=1)))
        self.assertEqual(result["pairs"][0]["relation"], "order_not_established")
        self.assertEqual(result["causation"], "not_established")

    def test_offset_equivalence_and_local_digits_difference(self):
        a = analyze(scenario(event(timestamp="2000-01-02T08:00:00-04:00")))["events"][0]
        b = analyze(scenario(event()))["events"][0]
        self.assertEqual(a["interval"], b["interval"])
        self.assertEqual(a["interval"]["lower_us"], T)
        c = analyze(scenario(event(timestamp="2000-01-02T08:00:00+04:00")))["events"][0]
        self.assertNotEqual(a["interval"], c["interval"])

    def test_raw_string_order_counterexample(self):
        a = event("A", "2000-01-02T08:00:00-04:00")  # UTC noon
        b = event("B", "2000-01-02T11:00:00Z")  # earlier despite bigger local digits
        self.assertLess(a["original_timestamp"], b["original_timestamp"])
        self.assertEqual(analyze(scenario(a, b))["pairs"][0]["relation"], "guaranteed_after")

    def test_z_negative_zero_original_offset_context(self):
        rows = [event("Z", "2000-01-02T12:00:00Z"), event("minus", "2000-01-02T12:00:00-00:00"), event("plus", "2000-01-02T12:00:00+00:00")]
        events = {row["event_id"]: row for row in analyze(scenario(*rows))["events"]}
        self.assertEqual(events["Z"]["interval"], events["minus"]["interval"])
        self.assertEqual(events["minus"]["original_timestamp"], rows[1]["original_timestamp"])
        self.assertEqual(events["minus"]["offset_context"], "original_local_offset_unknown")
        self.assertEqual(events["plus"]["offset_context"], "numeric_local_offset_declared")

    def test_unknown_reasons_preserve_partial_instant(self):
        row = event()
        row["quantization"] = row["clock_error_us"] = None
        row["timestamp_role"] = "unknown"
        result = analyze(scenario(row))["events"][0]
        self.assertEqual(result["status"], "unknown_context")
        self.assertEqual(result["unknown_reasons"], ["event_occurrence_role_not_established", "quantization_unknown", "clock_error_unknown"])
        self.assertIsNotNone(result["logged_utc"])
        self.assertIsNone(result["interval"])
        row["original_timestamp"] = "2000-01-02T12:00:00"
        result = analyze(scenario(row))["events"][0]
        self.assertIsNone(result["logged_utc"])
        self.assertIn("utc_context_missing", result["unknown_reasons"])

    def test_ingest_time_never_event_occurrence(self):
        row = event()
        row["timestamp_role"] = "ingest_time"
        result = analyze(scenario(row, event("B")))
        self.assertEqual(result["pairs"][0]["relation"], "unknown_context")

    def test_shared_source_no_error_cancellation(self):
        result = analyze(scenario(event(error={"min": -10000000, "max": 10000000}), event("B", "2000-01-02T12:00:02Z", error={"min": -10000000, "max": 10000000})))
        self.assertEqual(result["pairs"][0]["relation"], "order_not_established")

    def test_day_and_year_crossing(self):
        row = event(timestamp="2000-12-31T23:59:59Z", error={"min": -2000000, "max": 0})
        interval = analyze(scenario(row))["events"][0]["interval"]
        self.assertEqual(interval["upper_utc"], "2001-01-01T00:00:02.000000Z")

    def test_complete_pairs_and_input_order_invariant(self):
        data = scenario(*(event(f"E{i:02}") for i in range(32)))
        first = analyze(data)
        self.assertEqual(first["counts"]["pairs"], 496)
        self.assertEqual(len({(p["a"], p["b"]) for p in first["pairs"]}), 496)
        data["events"].reverse()
        second = analyze(data)
        # Exact-byte hash changes; model output and presentation do not.
        del first["input_sha256"], second["input_sha256"]
        self.assertEqual(first, second)

    def test_no_system_clock_and_input_immutability(self):
        data = scenario(event(), event("B"))
        before = copy.deepcopy(data)
        first = analyze(data)
        self.assertEqual(first, analyze(data))
        self.assertEqual(data, before)

    def test_controls_markup_json_preservation_and_bound(self):
        data = scenario()
        data["label"] = '<script>x</script>\n| [x](https://bad.example)\x1b[31m\u202e'
        result = analyze(data)
        encoded = lab.render(result, "json")
        self.assertEqual(json.loads(encoded)["label"], data["label"])
        self.assertNotIn(b"\x1b", encoded)
        text = lab.render(result, "markdown").decode()
        self.assertNotIn("<script>", text)
        self.assertNotIn("[x](", text)
        self.assertNotIn("\u202e", text)
        with patch.object(bio, "MAX_OUTPUT", 10), self.assertRaises(bio.InputError):
            lab.render(result, "json")


class FileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix=".test-timeline-", dir=ROOT)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "input.json"
        self.source.write_bytes(raw(scenario()))
        self.target = self.root / "report.json"

    def test_new_complete_file_and_no_overwrite(self):
        bio.write_new(self.target, b"complete", input_path=self.source)
        with self.assertRaises(bio.InputError):
            bio.write_new(self.target, b"bad")
        self.assertEqual(self.target.read_bytes(), b"complete")

    def test_input_alias_and_hardlink_refused(self):
        original = self.source.read_bytes()
        with self.assertRaises(bio.InputError):
            bio.write_new(self.source, b"bad", input_path=self.source)
        os.link(self.source, self.target)
        with self.assertRaises(bio.InputError):
            bio.write_new(self.target, b"bad", input_path=self.source)
        self.assertEqual(self.source.read_bytes(), original)

    def test_competing_creation(self):
        real_link = os.link
        def competitor(source, destination):
            Path(destination).write_bytes(b"other")
            return real_link(source, destination)
        with patch.object(bio.os, "link", side_effect=competitor), self.assertRaises(FileExistsError):
            bio.write_new(self.target, b"ours")
        self.assertEqual(self.target.read_bytes(), b"other")

    def test_link_and_flush_failures_no_partial_report(self):
        for method in ("link", "fsync"):
            with patch.object(bio.os, method, side_effect=OSError("synthetic")), self.assertRaises(OSError):
                bio.write_new(self.target, b"complete")
            self.assertFalse(self.target.exists())
            self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_post_publication_cleanup_warning(self):
        errors = io.StringIO()
        with patch.object(bio.Path, "unlink", side_effect=PermissionError("synthetic")), contextlib.redirect_stderr(errors):
            code = lab.main([str(self.source), "--output", str(self.target)])
        self.assertEqual(code, 3)
        self.assertIn("Complete report published", errors.getvalue())
        self.assertEqual(json.loads(self.target.read_bytes())["causation"], "not_established")

    def test_pre_publication_cleanup_state(self):
        with patch.object(bio.os, "link", side_effect=OSError("synthetic")), patch.object(bio.Path, "unlink", side_effect=PermissionError("synthetic")), self.assertRaises(bio.OutputCleanupError) as caught:
            bio.write_new(self.target, b"complete")
        self.assertFalse(caught.exception.published)
        self.assertFalse(self.target.exists())

    def test_cli_invalid_unknown_field_emits_no_report(self):
        data = scenario()
        data["events"].append(event("B", "2000-01-02T12:00:00"))
        data["events"][-1]["clock_error_us"] = {"min": 3, "max": 2}
        self.source.write_bytes(raw(data))
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = lab.main([str(self.source), "--output", str(self.target)])
        self.assertEqual(code, 2)
        self.assertFalse(self.target.exists())
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(str(self.source), errors.getvalue())

    def test_cli_deterministic_hash_and_output_exit(self):
        command = [sys.executable, *(["-O"] if sys.flags.optimize else []), str(ROOT / "timeline.py"), str(self.source), "--output", str(self.target)]
        first = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(first.returncode, 0, first.stderr)
        result = json.loads(self.target.read_bytes())
        self.assertEqual(result["input_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        second = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(second.returncode, 2)

    def test_missing_input_and_oversize_redacted(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(lab.main([str(self.root / "private-path")]), 2)
        self.assertNotIn("private-path", errors.getvalue())
        self.source.write_bytes(b" " * 65537)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lab.main([str(self.source)]), 2)

    def test_output_bounds_and_missing_parent(self):
        with self.assertRaises(bio.InputError):
            bio.write_new(self.target, b"x" * 1048577)
        with self.assertRaises(OSError):
            bio.write_new(self.root / "missing" / "report", b"report")
        self.assertFalse(self.target.exists())

    def test_ascii_stdout_encoding_failure_is_redacted(self):
        data = scenario()
        data["label"] = "安全"
        self.source.write_bytes(raw(data))
        output = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        self.addCleanup(output.close)
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = lab.main([str(self.source), "--format", "markdown"])
        self.assertEqual(code, 2)
        self.assertEqual(errors.getvalue(), "Rejected: output encoding failure\n")
        self.assertNotIn(str(self.source), errors.getvalue())

    def test_short_stdout_and_flush_failure_not_success(self):
        class ShortWriter(io.StringIO):
            def write(self, text):
                return super().write(text[:-1])
        class BadFlush(io.StringIO):
            def flush(self):
                raise OSError("private failure detail")
        for output in (ShortWriter(), BadFlush()):
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                code = lab.main([str(self.source)])
            self.assertEqual(code, 2)
            self.assertEqual(errors.getvalue(), "Rejected: OSError\n")


if __name__ == "__main__":
    unittest.main()
