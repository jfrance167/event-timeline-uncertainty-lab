# Research — October 5, 2026

## Reuse and distinct scope

Read vault Home.md, Codex Integration.md and **02 Research/Timestamp Normalization and Correlation Uncertainty.md**. The relevant note preserves original time, offset/assumptions, precision and unknown skew; warns against relabeling local time UTC and against causal conclusions from proximity. This is reference evidence, not operational authorization.

Read windows-event-log-investigation/README.md and its actual `parse_timestamp` implementation around lines 134–146. It requires timezone-aware strings and converts them to UTC; its event objects/detections/reports build point-based incident timelines. It has no STATE.md; that failed lookup is not evidence that the project lacks validation (README references VALIDATION.md). A bounded filename search also found other timestamp-oriented scenarios but no dedicated event-time uncertainty comparator. No exhaustive search or audit of unrelated projects is claimed.

The approved audit-policy lab already models retention/access/collector unknowns separately; Canary retains its own live detection gaps. Reuse conceptual input/output safeguards and verification patterns after approved implementation, without silently editing those labs or introducing shared runtime dependencies. A standalone script in a new folder can remain demonstrable independently; any copied local helper logic should be reviewed in its new context.

Compared candidates:

| Candidate | Distinct learning value | Fit/limitation |
|---|---|---|
| Event-time uncertainty intervals | Demonstrates conditional strict order versus overlap/missing context despite UTC normalization | Recommended; exact small synthetic model, no collection |
| Offline retention/evidence-window coverage | Shows whether supplied retained intervals could cover an investigation window | Useful later, but overlaps audit-policy retention unknowns and event-investigation visibility gaps; apparent window coverage does not establish complete logging |

Recommendation: build the first. No suitable complete small tool for the proposed contract was established in the bounded searches; dfdatetime is a valuable representation reference, not a reason to fork a larger forensic stack.

## Connected GitHub and strongest candidate

Connected GitHub search for Plaso succeeded; dfdatetime search and file fetches failed with transport errors. dfdatetime issue search succeeded. Read-only canonical public GitHub metadata/tree/blob access supplied the source inspection. Firecrawl was unavailable in the preceding research stage; no success is claimed here and no needless retry made. No upstream source was imported, installed or executed.

Candidate [log2timeline/dfdatetime](https://github.com/log2timeline/dfdatetime) inspected at revision **24e155547c7558c839ae923f0f6e2a7f1adbfedb**. Metadata: main branch, not archived, pushed_at 2026-09-27T05:11:08Z. README states its precision/accuracy preservation purpose. pyproject version 20260927 requires Python >=3.10 and build tools setuptools>=77/wheel, with no runtime dependency list there; this is not a full transitive audit. The inspected interface stores precision and timezone context but compares normalized scalar timestamps, including special handling for missing normalized values. It does not supply our proposed caller-bounded clock-error interval relation. Interface tests exist. Windows CI uses tox; its Actions are version tags, not immutable SHA pins. CI presence is not passing CI evidence.

Actual [Apache-2.0 license](https://github.com/log2timeline/dfdatetime/blob/24e155547c7558c839ae923f0f6e2a7f1adbfedb/LICENSE) read; pyproject includes acknowledgements/authors/license in license-files. Adopting source requires preserving applicable notices/license and documenting modifications; no copied source/vectors are planned. Issue [263](https://github.com/log2timeline/dfdatetime/issues/263) requests nanosecond-format parsing; [105](https://github.com/log2timeline/dfdatetime/issues/105) concerns precision setting. They illustrate format scope questions, not reproduced defects. No Scorecard, broad vulnerability/dependency audit or current upstream CI execution performed.

Evidence is inert text under .private/event-timeline-research-20261005. Inspected paths and Git blob IDs:

- README.md: acbd24ab48de7661685b326780f8bb2deecf2e4c
- LICENSE: d645695673349e3947e8e5ae42332d0ac3164cd7
- pyproject.toml: 1b1c7489ad8b39bb5f151705f1dc2384ef935766
- dfdatetime/interface.py: 5fa6e83c72d482235fb4df2478744dea90363582
- tests/interface.py: ab1a679ed4630bae791b804d12701cace888d378
- .github/workflows/test_windows.yml: e9a5b26966d255b5d546c9bd01a9ecc1dfd7e1fd

Some content endpoint/path probes returned no usable content; pinned Git blobs completed README/pyproject/CI retrieval. No inferred content for failed paths. Git blob IDs are upstream identity references; a whole checkout was not made.

## Primary sources and interpretation

[RFC 3339 §§4–5](https://www.rfc-editor.org/rfc/rfc3339.html) defines numeric-offset interpretation and limits conditions under which timestamp strings sort chronologically. It describes instants, not uncertainty intervals. Different offsets or fractional precision require normalization before any display ordering; precision digits alone do not measure accuracy.

[RFC 9557 §2](https://www.rfc-editor.org/rfc/rfc9557.html) updates RFC 3339's local-offset convention. Z and -00:00 can indicate a known UTC time without knowledge of the originating local offset. Do not equate -00:00 with a missing UTC instant or infer the source timezone from Z. Bracketed zone annotations and full IXDTF remain outside the initial contract.

[RFC 5424 §7.1](https://www.rfc-editor.org/rfc/rfc5424.html) describes distinct timezone/synchronization/accuracy metadata, including a maximum clock-error interpretation. It motivates bounded error intervals, not an assertion that real clocks have those bounds. The lab requires explicit caller-provided error bounds and will not infer a zero error from an isSynced-style flag or missing accuracy field. This is a deliberately conservative lab contract, not a syslog parser/conformance claim.

[Python 3.13 datetime documentation](https://docs.python.org/3.13/library/datetime.html) distinguishes aware/naive values, timezone conversion and repeated local times. The implementation should restrict input syntax, validate offset ranges and normalize explicit known instants; it must not use the local host timezone, guess DST folds or claim full RFC/leap-second support. Its microsecond resolution fits the proposed deliberately restricted model. No named-zone database dependency is needed.

The quantization conventions and comparison formula in PLAN.md are **proposed lab semantics**, not requirements derived from these standards. Conditional bounds do not authenticate data, prove clock synchronization or establish causation.

## Local-first drafting record

Defined a bounded six-test-idea brief: synthetic data only, no code/source claims, <=200 words, 400 tokens, 45-second timeout. The first invocation was denied loopback access by the app sandbox (EACCES), not a model-quality result. After that specific evidence, automatic review approved a local-only invocation outside the sandbox against the existing service. qwen3.5:2b returned 308 output tokens in 8.583 seconds, without downloads or external fallback.

Review rejected acceptance: identical local digits with differing offsets are not offset-equivalent; the touching-endpoint idea used T+epsilon without specifying interval endpoints; the quantization idea conflated error and resolution. Missing-context, signed-error and deterministic-output themes were useful but only after manual correction. Raw brief, failed metadata and complete draft remain separate from this reviewed plan. No generated code executed.

Explicit remote consideration: startup record reports degraded/unverified guardrails because the public free catalog is unavailable. No remote inference is necessary for source/security judgment, and no verified-free remote draft was attempted. No paid fallback, provider switch, signup, billing or quota assumptions. Laya categorization/triage does not resolve timestamp semantics and was not invoked.
