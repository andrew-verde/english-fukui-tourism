# ADR 0008: Thesis master scaffold fixes chapter numbering around §6

Date: 2026-07-02
Status: accepted

## Context

The forward roadmap called for folding §6 into "the thesis body proper," but no
thesis master document existed: `docs/thesis/` contained only the §6 chapter
and its seed skeleton, and the §4.x labels that §6 cross-references
(§4.1/§4.2/§4.3) originated as analysis-artifact numbering from the synthesis
stage (ADR 0006), not from any written chapter. §6's references to "Chapters 4
and 5" therefore resolved to nothing on disk, and a future chapter drafted
under a different numbering would silently break the finished §6 prose.

## Decision

Created `docs/thesis/thesis_master.md` as the normative master map rather than
renumbering §6 or waiting for chapters 1–5 to exist. The master document:

1. **Fixes the chapter map** (1 intro, 2 data/reproducibility, 3 DiD impact,
   4 diagnosis, 5 robustness, 6 intervention, 7 conclusion) so §6's internal
   references — "Chapters 4 and 5," "§4.3 priority matrix" — are resolvable by
   construction: §4.1/§4.2/§4.3 are declared as Chapter 4's subsection
   numbering, matching the synthesis artifact naming.
2. **Binds each chapter to its committed evidence artifacts and make targets**,
   so drafting chapters 1–5/7 is a writing task against a fixed evidence base,
   not a re-analysis.
3. **Freezes global figure numbering** at the existing fig1–fig7 file names
   (figs 1–3 synthesis, 4–5 causal robustness, 6 gap trajectories,
   7 durability); new figures append.
4. **Restates the house rules** (byte-for-byte numbers, Direction-B-is-a-design
   framing, ADR logging, full-chain re-runs after pipeline touches).

Every artifact path and headline number cited in the master was verified
against the committed file before citation (synthesis_narrative_metrics.json,
sem_stage2_results.csv, causal_robustness/metrics.json,
durability_mechanisms_tests.json, figure PNGs on disk).

## Consequences

- §6 is now wired into a defined thesis body; chapter drafting can proceed
  chapter-by-chapter against the fixed map without renumbering risk.
- No pipeline, test, or committed number changed; `reproduce-submission` did
  not need re-running (documentation-only round).
- The master is the single place a numbering or figure-order change must be
  recorded, alongside an ADR.

## Rejected alternatives

- **Renumber §6 to match some other scheme.** §6 is finished, verified prose;
  its numbering is internally consistent with the synthesis artifacts. Cheaper
  and safer to define the map around it.
- **Concatenate everything into one monolithic thesis file now.** Chapters 1–5
  are unwritten; a mostly-empty monolith invites drift between placeholder text
  and artifacts. Per-chapter files under a master map keep diffs reviewable.
- **Defer until chapters 1–5 are drafted.** Numbering would then be defined by
  whichever chapter lands first, repeating the §4.x ambiguity this ADR closes.
