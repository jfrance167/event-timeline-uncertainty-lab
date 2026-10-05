# Decisions — October 5, 2026

- Frozen synthetic JSON, no real exports/adapters. This keeps the learning question separate from existing collection/detection tools and privacy risks.
- Original stdlib implementation. Pinned dfdatetime representation source was inspected but scalar comparisons do not implement the proposed conditional error relation; no upstream code/tests adopted.
- Signed error is logged minus true UTC; interval subtraction reverses endpoints. Conservative closed quantization envelopes admit touching-boundary ambiguity and avoid false strict order.
- Integer microseconds and 2000–2099 local/normalized/expanded range; unsupported precision/leap seconds/zones rejected. Z/-00:00 retain known UTC but not original local offset.
- Provided assumptions always validated before unknown-context outcomes. No shared-source cancellation, continuity, inferred zero error or receipt-to-event conversion.
- Complete pair reports with stable ID presentation; overlap is not transitive and no total order/causation graph is claimed.
- Reused reviewed local bounded JSON and exclusive hard-link publication patterns without a runtime dependency on another app. Distinct file-cleanup and stdout failure outcomes documented.
- Trusted verification stores intentional sign/boundary regressions only in ignored fresh copies and checks original hashes unchanged; no source replacement/restore risk.
- Local draft rejected for incorrect tests. Remote verified-free readiness unavailable; no retries/provider switch/new spending. Codex retained security judgment and implementation/review.
- No parent staging/commits, repository/CI creation, hosted tests, publication, clock changes or new scheduler/chat. Coordinator approval covers the three local stages only.
