# Thesis Master Document — Friction, Conversion, and Intervention in Fukui Inbound Tourism

> **Role of this file.** This is the master map of the thesis. It fixes the
> chapter numbering that all chapter files cross-reference (in particular, the
> §4.x / §5 / Direction C / Direction B references inside
> `section6_intervention.md`), states each chapter's status, and binds every
> chapter to the committed evidence artifacts and `make` targets that
> regenerate its numbers. Chapter prose lives in per-chapter files in this
> directory (`sectionN_*.md`); this file carries structure, not argument.
>
> **Numbering is normative from this point on.** §6 was written against the
> chapter map below; new chapter drafts must adopt these numbers, and any
> renumbering is a deliberate decision that must update this file, the chapter
> files, and be recorded in `docs/adr/`.

## Working title

*From Statistical Diagnosis to Testable Intervention: Transport-Access
Friction and Station-to-Anchor Conversion in Fukui's Post-Shinkansen Inbound
Tourism.*

## The argument in one line

A transport-friction shock moves outcomes (DiD) → friction transmits through
satisfaction to intention (SEM) → transport access is the dominant, causally
credible constraint (synthesis + robustness) → durability is station-to-anchor
conversion, not repeat visitation (Direction C) → a pre-registered two-stage
nudge pilot tests the fix at its causal joint (Direction B).

## Chapter map

| Ch. | Title | Status | Chapter file |
|---|---|---|---|
| 1 | Introduction and motivation | **to draft** | — |
| 2 | Data, provenance, and reproducibility | **to draft** | — |
| 3 | Impact: the Hokuriku Shinkansen extension as a friction shock (DiD) | **to draft** | — |
| 4 | Diagnosis: where friction concentrates (SEM + synthesis) | **written** | `section4_diagnosis.md` |
| 5 | Robustness: is the demand signal real? (synthetic control, Direction D) | **written** | `section5_robustness.md` |
| 6 | From diagnosis to intervention (Directions C + B) | **written** | `section6_intervention.md` |
| 7 | Conclusion and transferable template | **to draft** | — |

Chapters 1–5 and 7 are unwritten as prose, but their quantitative content is
complete, committed, and test-guarded — drafting them is a writing task, not an
analysis task. The evidence base for each is fixed below.

## Evidence base per chapter

Every number printed in a chapter must be traceable to one of these artifacts,
byte-for-byte (see "House rules" at the end).

### Ch. 2 — Data, provenance, and reproducibility

- Sources and licensing: `docs/source_ledger.md`, `docs/data_reproducibility.md`.
- Method details: `docs/methods_appendix.md`.
- Reproduction contract: `docs/reproducibility_checklist.md`;
  `make reproduce-submission` (114 passed / 1 skipped; offline except
  `synth-causal-arm`, see ADR 0007).
- Provenance pins: Feed A `data/causal/fukui_municipalities_scm.csv`
  (sha256 `ff6cd1af…`, guarded by `test_input_feed_checksums`);
  DATA_COMMIT `dfb9069` (code4fukui japan-kanko-stat).
- ADRs: 0006 (feed join discipline), 0007 (network-claim reconciliation).

### Ch. 3 — Impact (DiD)

- Target: `make hokuriku-did-event-study`.
- Artifacts: `output/hokuriku_merged/did_event_study_report.md`,
  `did_thesis_estimates.csv`, `did_event_study.png`, `parallel_trends.png`.
- Headline: NPS +0.55 (earthquake-robust +0.65); revisit intention fragile —
  do not headline (see `docs/results_overview.md` §1 for the full verdict table).
- ADRs: 0001 (DiD + SEM as primary contribution), 0003 (locality-reservation arm).

### Ch. 4 — Diagnosis (SEM + synthesis join)

The **§4.1 / §4.2 / §4.3 subsection numbering referenced by §6 is fixed here**:

- **§4.1 diagnostic inputs: SEM damage paths + regime × friction map** —
  `output/synthesis/synthesis_regime_friction_map.csv`,
  Fig. 1 (`output/synthesis/figures/fig1_regime_friction_map.png`). The SEM
  results below are presented here as the chapter's first input.
- **§4.2 arrival-mode contrast** (lead mechanism) —
  `output/synthesis/synthesis_mode_friction.csv`, Fig. 2. Headline:
  transport_access 7.09% shinkansen vs 0.66% car vs 1.77% pooled-other (≈4.00×).
- **§4.3 priority × causal-opportunity matrix** —
  `output/synthesis/synthesis_priority_matrix.csv`, Fig. 3. transport_access is
  the unique ACT-NOW corner (priority_n = 1.000, causal_opportunity = 1.000).
- SEM: `make sem-ftas`; `output/sem/sem_stage1_results.csv` (n = 16,219;
  friction → satisfaction β = −0.21, satisfaction → intention β = 0.80,
  ≈73% mediated), `output/sem/sem_stage2_results.csv` (n = 2,565;
  transport_access β ≈ −0.123, p ≈ 1.2e-08),
  `output/sem/nudge_priority_ranking.csv`. Sample sizes per
  `output/sem/sem_fit_indices.csv` (authoritative over any prose summary).
- Machine-readable oracles: `output/synthesis/synthesis_narrative_metrics.json`.
- Targets: `make sem-ftas nudge-ranking synthesis synthesis-figures`.
- ADRs: 0001, 0006.

### Ch. 5 — Robustness (Direction D)

- Targets: `make synth-causal-arm causal-robustness robustness-figures
  gap-trajectories`.
- Artifacts: `output/national_stats/causal_robustness/metrics.json` (single
  source for: Fukui City opening-window +29.2%, one-sided in-space placebo
  p = 0.041 vs 1,538 well-fit donors, backdated-2023 in-time placebo silent at
  p = 0.47, well-fit significant set = {Eiheiji, Fukui City, Tsuruga, Sakai},
  leave-one-out range 26.2–39.8%), `inspace_placebos.csv`,
  `intime_placebo.csv`, `leave_one_out_fukui_city.csv`,
  `target_gap_trajectories.csv`; Figs. 4–5
  (`output/national_stats/causal_robustness/figures/`), Fig. 6
  (`output/synthesis/figures/fig6_gap_trajectories.png`).
- Parameters: EVENT_YM = 202403, INTIME_EVENT_YM = 202303,
  good_fit = pre_rmspe ≤ 0.15, RMSPE_FIT_MULT = 5.0.
- ADR: 0005.

### Ch. 6 — Intervention (written: `section6_intervention.md`)

- **Direction C (durability mechanism):**
  `output/synthesis/durability_mechanisms.csv` / `.md` /
  `durability_mechanisms_tests.json` (repeat-share anti-prediction:
  durable 50.2% vs transient 57.4%, z = −14.5), Fig. 7;
  corr(transport_access, leaked SCM lift) = 0.826 across 13 high-confidence
  municipalities (`synthesis_narrative_metrics.json`,
  key `transport_access_leaked_lift_corr_high_confidence`).
  Targets: `make durability-mechanisms durability-figures`.
- **Direction B (pre-registered pilot design, NOT evidence):**
  `experiments/nudge-pilot/DESIGN.md`, `power_analysis.md` / `.json`,
  `study-config.json`. Power plan: d = 0.25 is the car-vs-rail selection
  ceiling; n/arm at 80%: 252 (d = 0.25), 1,005 (d = 0.125), 1,570 (d = 0.10);
  Stage 1 n = 50/arm non-confirmatory; re-power rule d_plan = max(0.10, d̂ − se).
  Target: `make nudge-pilot-power`.
- ADR: 0007 (chapter decision log).

### Ch. 7 — Conclusion

- Draws only on numbers already printed in Chs. 3–6; the transferable-template
  framing is seeded in §6.5.

## Figure numbering (global, fixed)

| Fig. | Content | File |
|---|---|---|
| 1 | Regime × friction map | `output/synthesis/figures/fig1_regime_friction_map.png` |
| 2 | Arrival-mode friction contrast | `output/synthesis/figures/fig2_mode_friction.png` |
| 3 | Priority × causal-opportunity matrix | `output/synthesis/figures/fig3_priority_matrix.png` |
| 4 | In-space placebo distribution | `output/national_stats/causal_robustness/figures/fig4_placebo_distribution.png` |
| 5 | Backdated in-time placebo | `output/national_stats/causal_robustness/figures/fig5_intime_placebo.png` |
| 6 | Target gap trajectories | `output/synthesis/figures/fig6_gap_trajectories.png` |
| 7 | Durability mechanisms | `output/synthesis/figures/fig7_durability_mechanisms.png` |

New figures append (Fig. 8+); renumbering existing figures requires touching
the producing script, the chapter prose, and this table together.

## House rules for chapter drafting

1. **Numbers byte-for-byte.** Print verified values exactly as measured; if a
   number is not in a committed artifact, it does not go in the thesis.
2. **Direction B is a design.** All pilot-related prose stays framed as
   pre-registered design / future work until data exists.
3. **Decisions to `docs/adr/`.** Non-obvious calls (framing, exclusions,
   renumbering) get an ADR in the house format (0001–0007 as examples).
4. **Pipeline touches re-run the full chain.** Any change upstream of a printed
   number re-runs `make reproduce-submission` in full, not just changed tests.
5. **Municipality names carry JIS codes on first use** (18201 Fukui City,
   18202 Tsuruga, 18206 Katsuyama, 18208 Awara, 18210 Sakai, 18322 Eiheiji —
   full list in `data/causal/fukui_municipalities_scm.csv`).
