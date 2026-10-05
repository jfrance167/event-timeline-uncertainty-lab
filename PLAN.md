# Event timeline uncertainty lab — proposed plan

October 5, 2026. Tier 2. **Stages 1–3 approved by the authorized coordinator October 5 at 01:31.** Authority and evidence: STATE.md, RESEARCH.md and .private/coordination/2026-10-05/SUCCESSORS.md. Build a small Python standard-library educational comparator in this separate directory.

## Problem and success criteria

Normalized timestamp order can conceal quantization and clock uncertainty. Preserve the original timestamp and every supplied assumption; show only those strict event-time relations guaranteed by the proposed bounded model. Success is reproducible synthetic evidence showing disjoint intervals, overlaps/touching, unknown context and offset equivalence without claiming real-world accuracy, a total event order or causation.

Scope: <=32 synthetic events from <=8 neutral sources in explicit versioned JSON; UTC normalization, caller-declared quantization and signed clock-error intervals, conditional pairwise relations, bounded JSON/Markdown CLI and explanatory demos. No actual/sanitized logs in the initial contract, collectors, event detection, host clock/NTP calls, network, timezone guessing, DST database, syslog/EVTX/CSV adapters, latency correction, probability scores, clock calibration, causal graph, UI/server, dependencies or publication.

## Proposed input contract

Schema version integer 1; source kind exactly synthetic; neutral scenario label; unique restricted visible ASCII source/event IDs. Required event fields: event_id, source_id, original_timestamp, timestamp_role, quantization, clock_error_us. A scenario uses only bounded neutral labels; no arbitrary message bodies, usernames/hosts/accounts/commands.

Frozen root fields: schema_version, source_kind, label, sources, events, all required and no extras. sources is a list of unique case-sensitive IDs; events refer to those IDs. ID allowlist is [A-Za-z0-9][A-Za-z0-9_.-]{0,63}, no normalization. Empty sources/events are permitted and report zero pairs. Every supplied field is validated even when another context component is unknown; null only for quantization/clock_error_us, not required identity/timestamp/role fields. Local parsed dates, known normalized UTC values and complete expanded endpoints all must remain in 2000–2099. Invalid/unsupported input rejects the entire scenario rather than dropping rows.

Timestamp syntax: calendar date, T, seconds, optional 1–6 fractional digits, optional Z/numeric ±HH:MM suffix. Accept absence of suffix as an explicit unknown-context case, not UTC. Preserve Z/+00:00/-00:00 spelling; a -00:00 UTC instant is usable while original local-zone context remains unknown. Validate hour/minute ranges explicitly, including +00:60 rejection. Reject malformed calendars, leap seconds, >6 fractional digits, named/bracketed zones and numeric epoch formats as unsupported/invalid, with a clear reason; do not silently truncate or fix. This is a restricted profile, not full RFC conformance.

timestamp_role: event_time, ingest_time or unknown. Only event_time can form an event-time interval. An ingest timestamp describes receipt and cannot stand in for event occurrence without a separately modeled delay; that expansion is deferred.

quantization: null or {mode: truncated|rounded, quantum_us: one of 1,10,100,1000,10000,100000,1000000}. Declared resolution is independent of fractional digit count. Require the logged fractional value to align with its declared quantum; contradictory declarations are invalid, not guessed. A whole-second string can carry a declared microsecond quantum (subsecond digits may be omitted when zero); digit length is presentation, not measured precision.

clock_error_us: null or {min: signed integer, max: signed integer}; define **clock error = logged clock minus true UTC clock**. Both integers within ±86,400,000,000 microseconds and min <= max. Zero-width/zero-error bounds are permitted only as explicit synthetic assertions, never defaults or host measurements. Each event carries its own bounds; no inference that a shared source implies clock continuity, identical error or cancellation. No floating-point inputs or bool-as-integer.

Missing/null quantization or error, unknown timestamp role, or missing UTC context yields unknown_context and enumerated reasons. Valid partial context (e.g. normalized logged instant) can still be shown without inventing a complete interval. Missing required field is invalid schema; explicit null distinguishes intended unknown context. Unknown fields, duplicate JSON keys, duplicate IDs and dangling source references fail closed.

## Interval model and comparison

Use integer UTC microseconds, not float timestamp arithmetic. Restrict initial dates to 2000–2099; validate normalized UTC and expanded endpoints remain within that range. This avoids platform epoch conversion differences and overflow/clamping. No system clock is needed for comparison.

For logged UTC value t and declared quantum q:

- Truncated quantization uses the conservative **closed** logged-clock envelope [t, t+q]. The upper endpoint deliberately includes a boundary that an exact truncation model would exclude; reports state this conservatism.
- Rounded quantization uses [t-ceil(q/2), t+ceil(q/2)]. The one-microsecond case expands outward to integer microsecond endpoints; no sub-microsecond accuracy claim.
- Given signed error [e_min,e_max], event-time envelope is [logged_lower-e_max, logged_upper-e_min]. Positive logged-clock error shifts the true-time interval earlier.

These bounds are conditional on input assertions and on the declared event timestamp being taken at occurrence. No collection-delay model is implied. Do not convert precision into an error estimate or infer synchronization.

Compare every unordered pair, never silently truncate: A guaranteed_before B only when upper(A) < lower(B); reverse for guaranteed_after. Touching, overlapping and equal closed intervals return order_not_established, not simultaneous or equal real event time. Any missing complete interval returns unknown_context. Pair outputs include both IDs, conditional endpoints and reason. Relations are under the supplied model; no confidence percentage, shared-actor or causal conclusion.

Stable ID order is for presentation only. Reports must not present a sortable timestamp list as the proven timeline. Avoid merging overlapping intervals into equivalence classes: overlap is not transitive. No topological-sort or graph UI is needed initially. Pair count <=496 is complete for 32 events; unmodeled/invalid rows are never quietly dropped into a reassuring result.

## Architecture, dependencies and alternatives

Data-only parse -> strict validation -> normalized partial contexts -> pure conservative interval builder -> pure pair comparison -> JSON/Markdown renderer -> stdout or explicit exclusive new file. Report retains original timestamp, UTC logged value if known, declarations, assumption IDs/reasons, intervals, schema/model version, exact input SHA-256, resource limits and categorical causation-not-established statement. Hash binds bytes, not their truth or authenticity.

Reuse reviewed safety/verification patterns from audit-policy-coverage-lab after code approval; keep independently runnable APIs and tests rather than importing that app as a dependency. Standard datetime/timedelta/integer arithmetic/unittest meet this restricted scope. dfdatetime is broader and preserves valuable representation context, but inspected scalar comparisons do not replace this relation. No fork/adoption/runtime install recommended. Independent synthetic fixtures with hand-calculated expected bounds avoid a self-derived oracle.

Alternatives: a scalar UTC sort is simpler but omits uncertainty; full named-zone/DST resolution increases ambiguity and database dependency; retention-window coverage asks a useful different question but overlaps current visibility/retention work. Start with explicit-offset intervals and defer all three expansions.

## Threat model and resource/output bounds

Hostile input could exhaust the decoder/pair enumeration, exploit bool/numeric coercion or duplicate identity, inject report content, clobber evidence or induce unsupported chronological conclusions. Predecode cap 65,536 bytes, nesting 12, numeric token 20 characters; strings <=256 Unicode scalars, IDs <=64 visible allowlisted ASCII chars, <=8 sources, <=32 events, <=496 pairs, output <=1,048,576 bytes. Reject nonfinite/float numbers, invalid Unicode scalars, duplicate keys/IDs and unsupported versions. These are admission/report bounds, not a universal hard RSS/time guarantee. Bound filesystem reads; require trusted regular local files and directories.

Controls/bidi/format characters are sanitized for presentation while original data is preserved in structured escaped representation; no raw untrusted Markdown/HTML/terminal content. Fully render and bound before output. Exclusive complete-file publication, input/alias refusal, no overwrite and explicit pre/post-publication failure handling. No recursive cleanup. Filesystem/special-device/hostile-directory races and power-loss durability remain documented limits, as do false input assertions and untrusted Python/workspace modifications. Test errors must not print private paths/content.

## Stages and definitions of done

1. **Contract/parser and arithmetic**: document the restricted schema/model; create inert original fixtures and bounded parser, partial-context normalization and interval builder. Done when hand-calculated positive/negative-error and quantization examples pass; offset equivalence, unknown/malformed/unsupported forms, ranges and contradictory quantum alignment are explicit. No host API calls.
2. **Relations/reports/CLI**: all complete pair relations and reasons, original/normalized/declaration provenance, bounded JSON/Markdown, deterministic presentation and exclusive file output. Done when overlap/touching/equality never implies strict order or simultaneity, unknown context stays visible, arbitrary ID order never becomes event order, and complete pair/output limits hold.
3. **Verification/learning handoff**: meaningful unittest/CLI/error-path suite, exact source hashes/exit codes/full output, available SAST and actual ECC self-review/fixes, README/demo matrix/MIT/AI disclosure/security/DECISIONS/LEARNING/STATE, relevant vault milestone. Done when approved local checks pass and platform/live/accuracy limitations are stated. No publication or new repository without applicable authorization.

Required verification: equivalent offset representations (08:00-04:00 = 12:00Z); same digits with differing offsets are not equivalent; raw-string sort counterexample; touching endpoints, equal/contained/overlapping intervals, nontransitive overlap triple; signed error inversion and mixed signs; rounded odd quantum conservative expansion; truncated upper boundary; missing offset/error/precision/role; ingestion-time refusal; -00:00 context preservation; day/year crossing within bounds and endpoint overflow rejection; duplicate keys/source/event identities; float/nonfinite/bool values; oversized bytes/depth/tokens/count/strings/pairs/output; markup/bidi/control encoding; fixed data without system-clock dependency; input/output alias/hardlink, competing creation, failure before/after publication; all expected model results fixed independently. Optional focused mutations should change < to <= or flip error sign, prove detection, then restore and rerun.

Coordinator approved all three local stages with the frozen-schema/validation addendum above. Continue implementation/review/testing/docs within that scope. No new dispatch after 08:00 Eastern October 6; no new chats/schedulers, services, host changes, real logs, external messages, merge/deployment/publication.
