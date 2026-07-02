# ADR 0009: Chapter 4 drafting decisions and SEM sample-size reconciliation

Date: 2026-07-02
Status: accepted

## Context

With the thesis master scaffold in place (ADR 0008), Chapter 4 "Diagnosis:
where friction concentrates" was the next chapter to draft. Its evidence base
(SEM stages 1–2, synthesis join, priority matrix) is complete and test-guarded.
Drafting surfaced two issues: (1) the master map assigned §4.1 to the regime ×
friction map alone, leaving the SEM — which the §4.3 matrix consumes — with no
home before it is used; (2) `docs/results_overview.md` carried SEM sample sizes
and CFA loadings (n = 15,776 / 2,503; loadings .87/.53/.86) that do not match
the committed artifacts (`sem_fit_indices.csv`: n = 16,219 / 2,565;
`sem_stage1_results.csv` standardized loadings .87/.51/.84), presumably from an
earlier SEM run whose prose was never refreshed.

## Decision

1. **Wrote §4 (docs/thesis/section4_diagnosis.md)** with the structure
   4.0 purpose → 4.1 diagnostic inputs → 4.2 arrival-mode contrast →
   4.3 priority × causal-opportunity matrix → 4.4 boundaries.
2. **Widened §4.1 to "diagnostic inputs" (SEM + regime map)** rather than
   renumbering. This preserves both externally-bound references — §4.2 =
   arrival-mode contrast, §4.3 = priority matrix, as cited by §6 and the
   handoff record — while giving the SEM a home before the matrix uses its
   paths. The master map was amended in place; the regime map still lives in
   §4.1. Renumbering alternatives (SEM as §4.1 with everything shifting down)
   were rejected because they break the §4.3 reference inside the committed §6.
3. **The regime map forward-references Chapter 5** for the synthetic-control
   method it is built on. Chapter order (diagnosis before robustness) is worth
   this single forward reference; the alternative — moving the regime map into
   Chapter 5 — would strand the §4.1 dose–response corroboration away from the
   diagnosis it corroborates.
4. **Committed artifacts override stale prose: corrected results_overview.md**
   (n = 15,776 → 16,219; n = 2,503 → 2,565; loadings .87/.53/.86 → .87/.51/.84;
   ~72% → ≈73% mediated, recomputed as 0.206×0.802 / (0.206×0.802 + 0.063)).
   The chapter prints the artifact values. The master now names
   `sem_fit_indices.csv` as authoritative for sample sizes.
5. **All chapter numbers verified against committed artifacts before printing**,
   including recomputing the two-proportion z-statistics (51.5 vs car, 34.5 vs
   pooled) from the counts in `ftas_friction_by_transport_mode.csv`
   (744/10,493; 488/74,266; 1,674/94,514) and the mediation share from
   `sem_stage1_results.csv`. Values that superseded older summaries:
   food_amenities_gap causal_opportunity = 0.314 (matrix CSV; an earlier
   handoff note said 0.311), waiting/crowding shk-minus-other gap = 0.92 pp
   (CSV 0.9159; earlier note said ≈0.91).
6. **No separate skeleton file for §4.** The §6 skeleton was a cross-seat
   handoff artifact; §4 was structured and drafted in the same seat, so this
   ADR and the master's evidence bindings carry the provenance instead.

## Consequences

- Chapters 4 and 6 of the thesis body are now written; §6's recap of §4.2/§4.3
  points at real chapter prose whose numbers match byte-for-byte.
- results_overview.md is again consistent with the artifacts it summarizes; no
  pipeline, test, or committed artifact changed (documentation/prose round —
  reproduce-submission not re-run).
- Chapter 5 drafting inherits one obligation from §4.1's forward reference: it
  must introduce the SCM estimator that the regime map consumes.
