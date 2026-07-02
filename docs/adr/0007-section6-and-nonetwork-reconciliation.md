# ADR 0007: §6 intervention chapter and no-network claim reconciliation

Date: 2026-07-02
Status: accepted

## Context

Directions D (robustness), C (durability mechanism), and B (nudge-pilot design)
were implemented and committed (HEAD d0bf4fc). The thesis lacked a chapter tying
the §4 diagnosis, C's mechanism, and B's design into one argument. Separately, a
review of the reproduce-submission chain found that its user-facing documentation
claimed a flat "no-network" reproduction path, while the pipeline's own inline
Makefile comment (lines 37-40) correctly notes that the synth-causal-arm target
fetches the pinned code4fukui panel over the network to regenerate the Feed A
fixture (sha256 ff6cd1af...).

## Decision

1. **Wrote §6 "From Diagnosis to Intervention"** (docs/thesis/section6_intervention.md),
   seeded from docs/thesis/section6_skeleton.md. The chapter's spine: §4 establishes
   where friction concentrates (transport_access, shinkansen 7.09% vs car 0.66%),
   C explains why some municipalities convert the shock into durable demand
   (station-to-anchor last-mile conversion; repeat-visit share anti-predicts
   durability; Eiheiji/Sakai durable vs Fukui City transient), and B specifies the
   pre-registered two-stage nudge pilot that tests the mechanism at its causal joint.
   All verified numbers preserved byte-for-byte from committed artifacts. B is framed
   explicitly as pre-registered design, not evidence.

2. **Reconciled the no-network claim via documentation, not code (resolution "a").**
   Rejected the alternative (vendor/pre-stage the five city CSVs so Feed A reproduces
   from local files) because it risks disturbing the pinned Feed A checksum that the
   entire downstream chain trusts, for no analytic gain. Instead, amended three
   user-facing surfaces (Makefile help line, README, docs/reproducibility_checklist.md)
   to state "offline except synth-causal-arm (network fetch of pinned panel)," matching
   the already-honest inline Makefile comment. The Feed A producer and its checksum are
   untouched.

## Consequences

- The thesis now presents a complete diagnosis -> mechanism -> intervention arc.
- Reproduction documentation is internally consistent and honest about the single
  network dependency; no pipeline behavior or committed number changed.
- The mechanical doc edit was specified to and executed by Codex/gpt-5.5; the diff was
  independently reviewed (three files, five insertions, three deletions; inline comment
  block intact). The one residual "no-network" occurrence is the internal Makefile
  comment at line 37, which carries its own "Exception:" caveat two lines below and is
  therefore accurate in context.

## Rejected alternatives

- **Vendor/pre-stage the code4fukui CSVs (resolution "b").** Would eliminate the network
  call but only if Feed A reproduces byte-identically (ff6cd1af...) from local files; any
  drift would force a Feed A re-pin cascading through every downstream target. Not worth
  the checksum exposure for a documentation-honesty fix.
- **Editing the line-37 inline comment.** Left unchanged deliberately; it is already
  self-caveating and changing it risked reformatting the pre-staged-input documentation
  block.
