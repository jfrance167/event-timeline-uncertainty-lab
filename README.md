# Event timeline uncertainty lab

Compare synthetic event-time envelopes while preserving timestamp and clock assumptions. The tool distinguishes **conditional strict order**, **order not established**, and **unknown context**. It never infers causation, simultaneity, measured clock accuracy or a complete real-world timeline.

Python standard library only. No host clock/NTP calls, event/log collection, network, services, timezone database or external dependency. Fixtures are invented; this is not a production forensic tool.

## Run

Python 3.10+ is expected; verification uses Python 3.13.7 on Windows. Other runtimes/platforms are unverified. From this directory:

```powershell
python timeline.py fixtures/closed-boundaries.json --format markdown
python timeline.py fixtures/signed-error.json
python timeline.py fixtures/unknown-context.json --output new-report.json
```

Output defaults to JSON on stdout; `--format markdown` produces an explanatory report. `--output` requires a new destination in an existing trusted directory supporting hard links. Existing destinations/input aliases are refused. Use a UTF-8-capable terminal for Unicode Markdown labels or save a UTF-8 file; JSON output escapes Unicode.

| Demo | Expected lesson |
|---|---|
| closed-boundaries.json | A/B touch: order not established; C is strictly later than both under the declarations |
| signed-error.json | Logged-minus-true positive error moves true-time bounds earlier; negative error moves them later |
| unknown-context.json | Missing offset/error and receipt time remain unknown; -00:00 still identifies a UTC instant |

Optional exercise: compare A [0,1], B [.8,1.8], C [1.6,2.6] seconds. A overlaps B and B overlaps C, yet A is strictly before C. Overlap cannot form a transitive equivalence class.

## Frozen schema

See the fixtures for complete JSON. Root fields, all required: `schema_version` integer 1, `source_kind` exactly `synthetic`, nonempty neutral `label`, `sources` list of unique case-sensitive IDs, `events` list. Empty lists are valid. Unknown fields/duplicate JSON keys/duplicate IDs/dangling references reject the entire scenario. IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` and are not normalized.

Each event requires exactly:

- `event_id`, `source_id`: bounded IDs; source must be declared.
- `original_timestamp`: `YYYY-MM-DDTHH:MM:SS[.ffffff]` optionally followed by Z or numeric ±HH:MM. Fraction has 1–6 digits. Missing suffix is valid **unknown UTC context**, never guessed UTC. Z/-00:00 retain a known UTC instant without asserting the original local offset; +00:00 declares a numeric local offset. No region/DST inference.
- `timestamp_role`: `event_time`, `ingest_time` or `unknown`. Receipt time does not become event occurrence time without an independently modeled delay; no delay model exists here.
- `quantization`: null or exactly `{mode: "truncated"|"rounded", quantum_us: q}`; q is one of 1, 10, 100, 1000, 10000, 100000, 1000000. Logged fraction must align with declared quantum. Digit count never supplies accuracy/quantization automatically.
- `clock_error_us`: null or exactly `{min: integer, max: integer}` within ±86,400,000,000, min <= max. Error means **logged clock minus true UTC**. Zero error is only a supplied synthetic assertion, never a default.

All supplied fields are validated even when another assumption is unknown. Explicit null is allowed only for the two assumption objects; missing required fields are invalid. Local dates, known normalized UTC values and expanded endpoints must remain in 2000–2099. Malformed calendars/offsets, leap seconds, >6 fractional digits, named/bracketed zones, numeric epochs and unsupported forms reject the scenario without guessing, truncating or clamping. This is a restricted lab profile, not full RFC parsing.

## Model

Integer UTC microseconds avoid floating-point precision loss. For logged UTC t and quantum q:

| Declaration | Conservative closed logged-clock envelope |
|---|---|
| truncated | [t, t+q] |
| rounded | [t-ceil(q/2), t+ceil(q/2)] |

The truncated upper endpoint deliberately includes an extra boundary; rounded half-microsecond bounds expand outward. These are **declared lab conventions**, not claims about a device's behavior.

For error [e_min,e_max], true-event envelope is `[logged_lower-e_max, logged_upper-e_min]`. With t = noon, q = one second and error [2,3] seconds, the result is [11:59:57,11:59:59]. With error [-3,-2], it is [12:00:02,12:00:04]. These independent hand calculations anchor tests.

A is guaranteed_before B only if `upper(A) < lower(B)`; reverse yields guaranteed_after. Touching/overlap/equality means order_not_established, never simultaneity. Missing a complete interval means unknown_context with all missing reasons. Every unordered pair is reported; IDs sort presentation only. No shared-source cancellation or clock continuity is inferred. Every guarantee is conditional on unverified supplied assertions, including an occurrence-time timestamp. The input hash identifies bytes, not authenticity or event truth.

Primary references: [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html), [RFC 9557's local-offset update](https://www.rfc-editor.org/rfc/rfc9557.html#section-2), [RFC 5424 timeQuality](https://www.rfc-editor.org/rfc/rfc5424.html#section-7.1), [Python datetime](https://docs.python.org/3.13/library/datetime.html). Reviewed October 5, 2026; source claims and distinctions from our conventions are in [RESEARCH.md](RESEARCH.md).

## Safety and reusable APIs

Admission limits: 65,536 bytes, nesting 12 and numeric-token length 20 before JSON decoding. After decoding: strings <=256 Unicode scalars, <=8 sources, <=32 events and <=496 complete pairs. Output <=1,048,576 bytes. Strict UTF-8/no BOM, no floats/nonfinite numbers/bool-as-integer, invalid surrogates rejected. Cardinality limits are postdecode checks; these bounds do not promise hard RSS/time containment.

`validate(bytes)` validates the entire scenario. `event_interval(validated_event)` and `compare(normalized_a, normalized_b)` are pure model functions. `evaluate(validated_data, digest)` gives a deterministic report independent of the system clock. `render(report, format)` returns bounded UTF-8 bytes. `bounded_io.write_new(path, bytes, input_path=...)` safely publishes one new file. Direct internal APIs expect validated objects; the CLI is the input boundary. No functions execute input-selected code.

```text
Explicit synthetic bytes -> bounded JSON -> entire schema validation
                                      -> partial context / conditional envelopes
                                      -> all pair relations -> JSON / Markdown
```

Structured JSON preserves the original label through escaping; Markdown sanitizes control/format characters and encodes punctuation. Do not interpolate raw JSON into HTML. Reports never run content.

A flushed sibling temporary file is published with an exclusive hard link. Existing files/aliases are never overwritten. Failed publication cannot expose partial file output; a crash can leave a temporary file. Exit 0 = completed, 2 = rejected input/arguments or output failure, 3 = complete file published but temporary cleanup failed. Failure before publication with failed cleanup explicitly reports that no report was published. No recursive cleanup. Filesystem details are redacted from CLI diagnostics.

Stdout is nontransactional: short writes/encoding/flush errors return failure, but partial stdout may already exist. If stderr also fails, a reliable diagnostic is not promised. Hard-link support/app sandbox permissions, trusted local regular input/destination directories and a trusted Python/workspace are required. Special devices, hostile concurrent directory replacement and power-loss directory durability are outside protection. See [SECURITY.md](SECURITY.md).

## Verify and provenance

```powershell
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python verify.py
```

The verification helper uses the locally installed Bandit (1.9.4), never installs anything, and executes only trusted local checks. It captures full outputs, exact commands/exit codes, source hashes, six demos, normal/optimized tests and two isolated intentional mutants. Mutants are confined to ignored evidence copies; application source is checked unchanged. See [VERIFICATION.md](VERIFICATION.md) and [ECC_REVIEW.md](ECC_REVIEW.md).

Verified October 5, 2026: **44/44 tests in both normal and optimized execution**, four AST checks, six demos and Bandit exit 0. Both sign/boundary regressions detected, seven current hashes match; ECC self-review fixed two output paths. No hosted/live evidence implied.

Original code is MIT, copyright 2026 Jake Franciosa. No dfdatetime source or tests were copied; pinned Apache-2.0 candidate evidence was inspected only. Safety/verification patterns were adapted from Jake's local audit-policy lab. Codex assisted implementation, tests/docs and self-review; no independent review claimed. Local Ollama draft had incorrect test ideas and was rejected; raw evidence retained. No remote/paid fallback for implementation or real-clock evidence.

Jake subsequently authorized review and a separate private GitHub repository. Pinned test/Bandit and CodeQL workflows and Dependabot updates are prepared. Hosted workflows remain disabled pending verified included usage and private CodeQL eligibility; no hosted passes claimed. No paid activation or visibility changes. Runtime is stdlib-only; optional development Bandit version is pinned, transitive dependencies are not hash-locked. Local STATE/raw evidence are excluded from commits.
