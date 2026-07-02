# ADR 0013: Bookend chapters (1 and 7) and FTAS terminology fix

Date: 2026-07-03
Status: accepted

## Context

Chapters 2–6 were written across the preceding rounds (ADRs 0007–0012),
leaving the bookends. They were drafted together in one round so the
motivation (Chapter 1) and the contributions/limitations (Chapter 7) mirror
each other rather than drifting apart. During pre-drafting review of
CONTEXT.md — the canonical terminology source — a naming bug surfaced:
Chapters 2 and 4 expanded FTAS as "Fukui Tourism Attitude Survey," while the
domain charter defines it as "Fukui Tourism **Area** Survey."

## Decision

1. **Fixed the FTAS expansion** in section2_data.md and section4_diagnosis.md
   to "Fukui Tourism Area Survey" per CONTEXT.md. Canonical terms win over
   prose that invents its own expansion.
2. **Wrote §1 (docs/thesis/section1_introduction.md)**: motivation as a
   natural experiment on the regional-revitalization premise; the thesis
   question quoted from the domain charter; the argument in one paragraph
   with the chapter roadmap; stance (effect sizes over significance, honest
   limits as structure, reproducibility as method).
3. **Wrote §7 (docs/thesis/section7_conclusion.md)**: findings recap printing
   only numbers already established in Chapters 3–6 byte-for-byte;
   contributions (empirical, mechanistic, methodological); consolidated
   limitations mapped one-per-design; future work leading with the two-stage
   pilot execution path and its live feasibility flag (~1,000/arm if the
   nudge closes half the ceiling), then DOI deposit and template repetition.
4. **No new numbers were introduced in either chapter.** Both cite
   `make reproduce-submission` as the blanket reproduction path, satisfying
   the provenance guard (§7 prints p = 0.041).
5. **Master map updated**: all seven chapters marked written; the stale
   "chapters unwritten" paragraph replaced with a traceability-preservation
   rule for revisions.

## Consequences

- The thesis body (Chapters 1–7) is complete in prose under the fixed chapter
  map; §6's cross-references resolve against written chapters in both
  directions.
- Remaining before submission: the full-thesis coherence pass (numbers,
  figure ordering, cross-references, ADR trail) and one complete
  `reproduce-submission` run as the final gate.
- Docs-only round; no pipeline or artifact changed.
