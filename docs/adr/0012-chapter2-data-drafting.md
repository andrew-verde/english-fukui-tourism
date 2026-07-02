# ADR 0012: Chapter 2 drafting decisions — provenance guard fix and ledger sync

Date: 2026-07-03
Status: accepted

## Context

Chapter 2 "Data, provenance, and reproducibility" was drafted per the master
map (ADR 0008), absorbing the licensing/provenance detail as ADR 0011
directed. Evidence base: `docs/data_reproducibility.md`,
`docs/source_ledger.md`, `docs/methods_appendix.md`,
`docs/reproducibility_checklist.md`, the source manifests, and
`output/official_fukui/statistical_results_official.json`. Running the full
test suite as an oracle check surfaced three failing provenance-guard params
(`tests/test_report_provenance.py`): the committed
`section6_intervention.md`, `section6_skeleton.md`, and ADR 0010 contained
p-value claims without a `make` target or `scripts/` path — the guard is
parametrized over `docs/**/*.md`, so each newly committed doc becomes a new
test case, and §6 predated the convention the newer chapters follow.

## Decision

1. **Fixed the guard failures before drafting** (committed separately as
   6942dec): added reproduction commands to both §6 files and qualified
   `causal_robustness.py` with its `scripts/` prefix in ADR 0010. Suite green
   at 131 passed, 1 skipped. Alternative rejected: deleting the skeleton —
   it is Andrew's committed provenance artifact; not this seat's call.
2. **Wrote §2 (docs/thesis/section2_data.md)**: 2.0 the traceability rule →
   2.1 data families (survey microdata, visitor-count panel, supporting
   series, quarantined side project) → 2.2 provenance discipline (lock file,
   manifests, ledger, LFS, the two load-bearing gates: Feed A sha256 and the
   provenance guard itself) → 2.3 units and measurement → 2.4 the
   reproduction contract.
3. **Framed provenance discipline as the chapter's methodological
   contribution** (all data is public open data; the machinery is the work),
   and presented the provenance guard as the chapter's own rules being
   enforced by `make test` — including on this very chapter.
4. **Printed the current test count (131 passed, 1 skipped)** as "at this
   writing", replacing the stale 114/1 from earlier notes; the count grows
   with each committed doc by construction of the guard.
5. **Synced two stale source-ledger cells** with the committed artifacts and
   Chapters 3–4: SEM mediation ~72% → ≈73% (per ADR 0009's recomputation) and
   DiD transport satisfaction +0.05 → +0.055 (robust +0.077).
6. Verified this round from artifacts: dedup counts (97,866 → 51,399; 46,467
   dropped) and the 15.4% inconvenience rate (7,908/51,399) from
   `statistical_results_official.json`; the CC-BY chain from
   `source_manifest.json`; the Feed A sha256 pin in both test modules; test
   counts by running the suite.

## Consequences

- Chapters 2–6 are written; only the intro (1) and conclusion (7) remain.
- The suite is green again and will stay a gate: every future chapter file
  is automatically a provenance-guard test case.
- Docs-only round except the guard fixes; no pipeline or artifact changed;
  reproduce-submission not re-run (test target run directly instead).
