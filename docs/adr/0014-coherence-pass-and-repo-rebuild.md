# ADR 0014: Coherence pass, Git LFS reality fix, and clean-repo rebuild

Date: 2026-07-03
Status: accepted

## Context

With all seven chapters written (ADRs 0007–0013), the closing roadmap items
were the full-thesis coherence pass and a complete `reproduce-submission`
run. Separately, Andrew decided the repository's history — accumulated
through multiple design changes — should be archived as-is, with the
semi-final version rebuilt into a new repository with a clean history.
Pre-rebuild inspection surfaced a documentation falsehood: three docs (and
thesis §2, which inherited the claim) stated that raw microdata is tracked
in Git LFS, but the repository tracks 127 files, has no `.gitattributes`,
and `git lfs ls-files` is empty — raw inputs are in fact re-materialized by
the fetch targets from immutable commit-addressed URLs verified against
source-manifest SHA-256 values.

## Decision

1. **Corrected the LFS claim to describe reality** in
   `docs/data_reproducibility.md`, `docs/reproducibility_checklist.md`, and
   `docs/thesis/section2_data.md`: microdata is not committed; a fresh clone
   reproduces it via pinned fetches with hash verification. The alternative —
   actually implementing LFS tracking — was rejected as a pre-archive change:
   it would rewrite the repo's data-handling contract at the moment of
   freezing it, for no reviewer benefit the fetch+verify path doesn't already
   provide.
2. **Coherence fixes from the end-to-end read of Chapters 1–7** (all in §6,
   the earliest-written chapter): (a) transport_access is the unique occupant
   of the ACT-NOW *corner* (max of both axes), not of the quadrant, which
   also contains opening_hours_availability and food_amenities_gap per the
   matrix CSV; (b) the well-fit significant set is qualified with its 10%
   one-sided threshold (§5.3); (c) Fig. 7 is now cited at the r = 0.826
   corroboration — previously the only globally numbered figure uncited in
   prose. All other cross-chapter numbers, figure references, JIS-code first
   uses, and hand-offs checked consistent.
3. **Repo rebuild:** `english-fukui-tourism` becomes the project archive;
   the tree at this commit is exported (no history) as the initial commit of
   a new repository, with untracked pre-staged inputs copied alongside so the
   local checkout reproduces immediately, a fresh venv, and the full
   `reproduce-submission` chain run as the acceptance gate before the initial
   commit is pushed. The new README points back to this archive for the
   development history and ADR provenance context.

## Consequences

- The thesis and its reproduction documentation describe the same repository
  a reviewer actually receives.
- The archive's final state is coherent; the new repository inherits it
  byte-for-byte (minus history) with a verified green chain.
- Docs-only changes in this repo; the pipeline gate runs in the new checkout.
