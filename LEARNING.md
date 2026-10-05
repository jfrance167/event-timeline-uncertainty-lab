# Learning

UTC normalization fixes representation differences; it does not fix clock error or prove timestamp accuracy. 08:00-04:00 equals noon UTC; identical 08:00 digits with +04:00 do not represent that instant.

Positive logged-minus-true error means the clock is fast. Subtract the maximum error from the lower bound and the minimum from the upper. Swapping the sign/endpoints can manufacture an incorrect chronological relation.

Closed envelopes that touch may share a possible time. Use strict disjointness for guaranteed order. Overlap is not transitive: overlapping pairs must not be merged into an equivalence group. Equality of envelopes cannot prove simultaneous occurrence.

Missing context is different from invalid provided data. A null error does not excuse a contradictory quantum, and missing offset does not excuse reversed error bounds. Unknown outcomes preserve valid partial context without legitimizing malformed assertions.

Self-review reproduced an uncaught Unicode stdout encoding error and false success on short stdout writes. Fixed diagnostics and flushing help report failure; stdout still cannot be rolled back transactionally. Exclusive complete file publication solves a different problem.

The local small-model draft was fluent but gave wrong offset-equivalence and endpoint ideas. Hand-calculated test oracles and source review remained necessary. Intentional sign/boundary mutations show specific regression sensitivity, not universal security coverage.
