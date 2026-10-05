"""Local tests, bounded demos, isolated regression mutations and evidence capture."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
# Trusted verification launches only the selected Python and fixed local checks.
import subprocess  # nosec B404
import sys

ROOT = Path(__file__).resolve().parent


def execute(command, directory, stem):
    # Callers supply reviewed Python/module/script arguments; no shell or input code.
    result = subprocess.run(command, cwd=directory, capture_output=True, timeout=60, shell=False)  # nosec B603
    stem.with_suffix(".stdout.txt").write_bytes(result.stdout)
    stem.with_suffix(".stderr.txt").write_bytes(result.stderr)
    return result


def main():
    run = ROOT / "verification-runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True, exist_ok=False)
    sources = sorted([*ROOT.glob("*.py"), *ROOT.glob("tests/*.py"), *ROOT.glob("fixtures/*.json")])
    hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    syntax = []
    for source in sources:
        if source.suffix == ".py":
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            syntax.append(source.relative_to(ROOT).as_posix())
    checks = []
    for name, mode in (("normal", []), ("optimized", ["-O"])):
        command = [sys.executable, *mode, "-W", "error", "-m", "unittest", "discover", "-s", "tests", "-v"]
        result = execute(command, ROOT, run / name)
        checks.append({"name": name, "command": command, "exit_code": result.returncode})
    demos = []
    for fixture in sorted(ROOT.glob("fixtures/*.json")):
        for format_name in ("json", "markdown"):
            command = [sys.executable, "timeline.py", str(fixture.relative_to(ROOT)), "--format", format_name]
            result = execute(command, ROOT, run / (fixture.stem + "-" + format_name))
            demos.append({"command": command, "exit_code": result.returncode})
    mutations = []
    original = (ROOT / "timeline.py").read_text(encoding="utf-8")
    for name, before, after, target in (
        ("closed-boundary", 'left["upper_us"] < right["lower_us"]', 'left["upper_us"] <= right["lower_us"]', "test_truncated_closed_upper_and_touch"),
        ("clock-sign", 'lower = logged_lower - error["max"]', 'lower = logged_lower + error["max"]', "test_hand_calculated_positive_error"),
    ):
        if original.count(before) != 1:
            raise RuntimeError("mutation anchor must be unique")
        directory = run / ("mutation-" + name)
        (directory / "tests").mkdir(parents=True, exist_ok=False)
        (directory / "timeline.py").write_text(original.replace(before, after, 1), encoding="utf-8")
        (directory / "bounded_io.py").write_bytes((ROOT / "bounded_io.py").read_bytes())
        (directory / "tests/test_timeline.py").write_bytes((ROOT / "tests/test_timeline.py").read_bytes())
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-k", target, "-v"]
        result = execute(command, directory, run / ("mutation-" + name))
        text = result.stderr.decode(errors="replace")
        detected = result.returncode == 1 and "FAIL: " + target in text and "AssertionError" in text and "ERROR:" not in text
        mutations.append({"name": name, "command": command, "exit_code": result.returncode, "detected_assertion_failure": detected,
                          "mutant_sha256": hashlib.sha256((directory / "timeline.py").read_bytes()).hexdigest()})
    sast_command = [sys.executable, "-m", "bandit", "-r", "timeline.py", "bounded_io.py", "verify.py", "-f", "json"]
    sast = execute(sast_command, ROOT, run / "bandit")
    current_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in hashes}
    unchanged = hashes == current_hashes
    record = {"python": sys.version, "executable": sys.executable, "syntax": {"status": "PASS", "files": syntax},
              "tests": checks, "demos": demos, "mutations": mutations, "bandit": {"command": sast_command, "exit_code": sast.returncode},
              "source_sha256": hashes, "source_unchanged_after_mutations": unchanged,
              "limits": {"real_clock_accuracy": "NOT APPLICABLE: synthetic assertions", "host_collection": "NOT APPLICABLE: offline scope", "CodeQL_hosted_CI": "NOT RUN: no standalone owned repository/publication"}}
    (run / "report.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(run / "report.json")
    print(json.dumps({"tests": checks, "demo_count": len(demos), "mutations": mutations, "bandit_exit": sast.returncode, "source_unchanged": unchanged}, indent=2))
    return 0 if all(c["exit_code"] == 0 for c in checks + demos) and all(m["detected_assertion_failure"] for m in mutations) and sast.returncode == 0 and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
