# Verification — October 5, 2026

Final evidence: `verification-runs/20261005T054532177480Z/report.json`, wrapper exit 0, Python 3.13.7 on Windows. Full stdout/stderr, exact commands/exit codes/runtime, seven source SHA-256 hashes and unchanged-after-mutations status captured. All seven hashes rechecked and match current code/fixtures; docs are not included in those hashes.

| Check | Result | Evidence |
|---|---|---|
| Python AST | PASS | four files, syntax record |
| Normal tests, warnings as errors | PASS | 44 tests, exit 0, normal.stderr.txt |
| Optimized tests (-O), warnings as errors | PASS | 44 tests, exit 0, optimized.stderr.txt; child CLI tests inherit -O |
| Three fixtures × JSON/Markdown | PASS | six demos, all exit 0, full outputs |
| Strict-boundary mutation | PASS (detected) | isolated < to <=, expected touching assertion failure, exit 1 |
| Clock-sign mutation | PASS (detected) | isolated lower-bound minus to plus, expected positive-error assertion failure, exit 1 |
| Original source after mutations | PASS | unchanged hashes, no source replacement/restore |
| Installed Bandit 1.9.4 | PASS | exit 0, zero results; two narrow reviewed verifier suppressions |
| Code/fixture hashes | PASS | seven current matches |
| Scoped credential patterns | PASS for scanned forms | zero private-key/GitHub/AWS patterns; not comprehensive |
| Real clock/host collection | NOT APPLICABLE | synthetic offline assertions |
| Hosted CI/CodeQL | NOT RUN | no standalone repository/publication authorized |
| Other runtimes/platforms | NOT RUN | no portability verification claimed |

Behavior checks cover schema/identity/resource/range rejection, supplied malformed assumptions despite other unknowns, independent positive/negative/mixed sign examples, rounding/truncation, closed-touch/equal/contained/nontransitive overlaps, UTC equivalents/raw-sort counterexample/Z/-00:00, missing/receipt context, shared-source uncertainty, complete 496 pairs/order invariance, immutable deterministic analysis, report injection/encoding, exclusive output/aliases/competition and link/flush/cleanup/short-stdout errors with redacted diagnostics.

Pre-review run `20261005T054309227647Z` preserved 42 normal/optimized tests plus demos/mutations/Bandit. Initial direct invocation had a bytes-literal SyntaxWarning; fixture switched to raw bytes before recorded warnings-as-errors checks. ECC then reproduced/fixed encoding and short/flush output paths, adding two tests. Mutant/failure evidence preserved.

Automatically approved filesystem checks ran outside app sandbox for hard-link support without Windows elevation, host clock/NTP/policy/log/SACL/service changes. Trusted verifier launches local checks without a shell/network/downloads. Passing checks are bounded evidence, not event truth, measured synchronization/causation or universal security. Stdout remains nontransactional; file publication is complete/exclusive under documented trusted-filesystem assumptions.
