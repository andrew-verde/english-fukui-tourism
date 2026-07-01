# Codex Handoff — synthesis-stage friction × causal arm for english-fukui-tourism

**Prepared by:** Claude (orchestration side) · **Implemented by:** Codex on Linux desktop
**Branch:** `main` · **Event date used throughout:** `2024-03-16` (Hokuriku Shinkansen Kanazawa–Tsuruga extension)

This wires the already-computed synthesis analysis into the repo as a reproducible
`make` target with a test. **All analysis logic below was run and validated Claude-side**;
the numbers in §5 are the **test oracle** — Codex's implementation must reproduce them
(within the stated tolerance) or a feed is stale and must be regenerated, not silently
re-pinned.

> **Apply as diffs, not prose.** Every block names its target file and slot. Nothing here
> invents a statistic the repo doesn't already produce — it adds ONE script
> (`scripts/synthesis_friction_causal.py`), ONE Makefile target (`synthesis`), ONE test
> (`tests/test_synthesis_friction_causal.py`), and ONE ADR (`docs/adr/0006-*.md`). It reuses
> the existing `output/sem/` and `output/official_fukui/` feeds and the causal-arm summary CSV.

---

## 0. Dependency graph — read before writing the loader

The synthesis script is **pure post-processing**: it reads four existing CSVs and writes
three CSVs + one narrative. It runs **no SEM, no SCM, no fetch**. Its inputs are produced by
targets that must run first:

```
build-ftas   → output/official_fukui/ftas_friction_by_municipality.csv   (Feed B)
             → output/official_fukui/ftas_friction_by_transport_mode.csv  (Feed B′)
sem-ftas     → output/sem/sem_stage2_results.csv, sem_fit_indices.csv     (SEM)
nudge-ranking→ output/sem/nudge_priority_ranking.csv                      (Feed C)
[causal arm] → data/causal/fukui_municipalities_scm.csv                   (Feed A) ★
```

★ **Feed A gotcha.** `fukui_municipalities_scm.csv` (per-municipality `open_pct`, `sust_pct`,
`good_fit`, `rmspe_ratio`, `p_meangap`, `p_ratio`) is the **causal arm's committed summary
artifact**, NOT emitted by the current `scripts/synthetic_control_fukui.py` (which writes
`{label}_gap.csv`, `{label}_weights.csv`, `report.json` per target under
`output/national_stats/synthetic_control/`). Treat Feed A as a **committed input** living at
`data/causal/fukui_municipalities_scm.csv`. The synthesis target must **assert its
presence and checksum** and fail with a clear message if missing — do NOT try to regenerate it
from the SCM script. (If the team later wants it regenerated, that is a separate aggregation
task; out of scope here.)

**RESOLVED:** Feed A is now tracked at
`data/causal/fukui_municipalities_scm.csv`, so fresh clones receive the pinned
cross-arm input.

---

## 1. New script — `scripts/synthesis_friction_causal.py`

Follow the house pattern of `scripts/rank_nudge_priorities.py` (module docstring, `ROOT =
Path(__file__).resolve().parent.parent`, `main() -> int`, argparse with `--output-dir`
default). Structure:

```python
#!/usr/bin/env python3
"""Synthesis stage: join causal-arm regime classification to FTAS friction feeds.

Reads (all pre-existing):
  data/causal/fukui_municipalities_scm.csv                  (Feed A, causal arm summary)
  output/official_fukui/ftas_friction_by_municipality.csv   (Feed B)
  output/official_fukui/ftas_friction_by_transport_mode.csv (Feed B')
  output/sem/nudge_priority_ranking.csv                     (Feed C)

Writes (output/synthesis/ by default):
  synthesis_regime_friction_map.csv    (§4.1)
  synthesis_mode_friction.csv          (§4.2)
  synthesis_priority_matrix.csv        (§4.3)
  synthesis_narrative_metrics.json     (machine-readable oracles for the test)
"""
```

Implement these steps **exactly** (they reproduce the validated Claude-side computation):

### 1a. §3 join (Feed A ⋈ Feed B)
- Pivot Feed B to municipality × friction_code on `pct_of_respondents` (fill 0). 12 friction
  codes, 17 municipalities.
- Join to Feed A on the **Japanese `name`** column (福井市 etc.) via **exact string match** —
  NO fuzzy matching. Assert 17/17 matched, 0 unmatched either side; raise on any miss.
- Carry `area_code`, `en`, `open_pct`, `sust_pct`, `good_fit` onto the pivot.

### 1b. §4.1 regime classification
```
regime = 'durable'   if open_pct > 5 and sust_pct >= 0
         'transient' if open_pct > 5 and sust_pct <  0
         'none'      otherwise
regime_confidence = 'high' if good_fit else 'low'   # confidence FLAG, not a reclassifier
leaked_lift_pct   = max(open_pct - sust_pct, 0) if open_pct > 5 else 0
```
Emit `synthesis_regime_friction_map.csv`: one row per municipality with area_code, en,
municipality (JP name), regime, regime_confidence, good_fit, open_pct, sust_pct,
leaked_lift_pct, transport_access_pct, wayfinding_signage_pct, food_amenities_gap_pct,
top1/top2/top3_friction (code + pct). Sort by regime (durable, transient, none) then open_pct desc.

### 1c. §4.2 arrival-mode contrast (Feed B′)
- Arrival modes = `transport_to_fukui_*`. Visitor arrival modes EXCLUDE
  `transport_to_fukui_local_resident`.
- For each friction code: `shinkansen_pct`, `private_car_pct`, and `other_arrival_pooled_pct`
  = respondent-weighted mean prevalence across non-Shinkansen visitor arrival modes
  (airplane, local_train, private_car, rental_car, tour_bus). Compute `shk_minus_car`,
  `shk_minus_other`, `shk_over_other_ratio`.
- Merge SEM `priority_score`, `sem_path_to_satisfaction_std`, `p_value` from Feed C.
- Emit `synthesis_mode_friction.csv`, sorted by `shk_minus_other` desc.

### 1d. §4.3 priority × causal-opportunity matrix
- For the 8 SEM-scored friction codes: normalize (min-max) three signals —
  `shk_over_other_ratio`, `leaked_lift_corr` (clipped ≥0), `|sem_path|` — and set
  `causal_opportunity = mean` of the three normalized values (round 3).
  `leaked_lift_corr` = Pearson corr of each code's prevalence with `leaked_lift_pct`
  across the **high-confidence** municipalities only.
- `priority_n` = min-max of `priority_score` clipped ≥0.
- `quadrant` by median split of (`priority_n`, `causal_opportunity`): both-high → "ACT NOW";
  priority-high only → "quick win"; causal-high only → "watch"; else "deprioritize".
- Emit `synthesis_priority_matrix.csv`, sorted by causal_opportunity then priority_score desc.

### 1e. Metrics JSON (for the test)
Write `synthesis_narrative_metrics.json` with the oracle scalars in §5 below.

**Figures are out of scope for this target** (they were produced Claude-side and saved as
artifacts). If the team wants them regenerated in-repo, add a separate `synthesis-figures`
target later; do not couple plotting into this data target.

---

## 2. `Makefile` — new target

Insert after the `nudge-ranking:` block, matching its two-line form:

```make
synthesis:
	$(PYTHON) scripts/synthesis_friction_causal.py
```

Add `synthesis` to the `reproduce-submission:` prerequisite chain, **after** `sem-ftas` and
`nudge-ranking` (it depends on their outputs):

```make
reproduce-submission: test build-ftas stats-official synth-official sem-ftas nudge-ranking synthesis hokuriku-did-event-study data-manifest
```

---

## 3. Test — `tests/test_synthesis_friction_causal.py`

Follow `tests/test_synthetic_control_fukui.py` conventions (pytest, module-level fixtures
reading the emitted CSVs, `skip` if the target hasn't been run). Assert against the §5 oracles.
Key assertions:

1. **Join completeness:** regime map has exactly 17 rows; no null regime; the set of
   `en` equals the 17 known municipalities.
2. **Regime counts** match §5.1 exactly.
3. **§4.2 headline:** `transport_access` row has `shinkansen_pct` ≈ 7.09, `private_car_pct`
   ≈ 0.66, `other_arrival_pooled_pct` ≈ 1.77, `shk_over_other_ratio` ≈ 4.0 (atol per §5).
   Assert `transport_access` is the **argmax** of `shk_minus_other`.
4. **§4.3:** `transport_access` is the **only** row with `quadrant == "ACT NOW ..."` **and**
   `causal_opportunity == 1.0` **and** `priority_n == 1.0`.
5. **Input integrity:** assert the four input checksums in §4 (guards against a silently
   changed feed). Use a helper that reads the pinned sha256 and `pytest.fail`s with the path
   if it drifts — do NOT auto-update.

---

## 4. Input feed checksums (pin these in the test)

Computed Claude-side from the validated feeds. If any drifts, the upstream target changed —
regenerate and re-derive the oracles, do not edit the checksum to pass.

| Feed | Path | rows | sha256 |
|---|---|---|---|
| A (causal) | `data/causal/fukui_municipalities_scm.csv` | 17 | `ff6cd1afecb0ec1175434cba0ab9964511fe9167ef57166c50e8ba713f84d953` |
| B | `output/official_fukui/ftas_friction_by_municipality.csv` | 216 | `a5c6304c97a76775fa2f35f9dd222e6296c70e9dddd7bace19d3290be9769192` |
| B′ | `output/official_fukui/ftas_friction_by_transport_mode.csv` | 132 | `52a74615198651a8e08d45562aef719002b20a34e55695fcfb3b1a423e6dd64f` |
| C | `output/sem/nudge_priority_ranking.csv` | 8 | `b21eb787783f3f5b67c47c14d8665bc699b92ff637e609ddbc1c39eac6d882b8` |

*(These are the workspace copies used in the Claude-side run. If the repo's own
`build-ftas`/`nudge-ranking` produce byte-identical files, these match; if the repo pins a
different upstream commit, re-run those targets first and re-derive §5 rather than forcing a
match.)*

---

## 5. Oracles — the numbers the implementation MUST reproduce

**§5.1 Regime counts** (all 17 / high-confidence subset):
```
all:  none=8, transient=6, durable=3
high: none=7, transient=4, durable=2   (Katsuyama durable-low, Ikeda & Mihama transient-low)
```

**§5.2 §4.1 dose-response** — Pearson corr(transport_access prevalence, leaked_lift_pct)
across the 13 high-confidence municipalities = **0.83** (atol 0.02). Transient high-conf
mean transport_access = 2.86% vs non-transient 1.73%.

**§5.3 §4.2 arrival-mode headline** (`transport_access`):
```
shinkansen_pct           = 7.09   (744 / 10493)   atol 0.05
private_car_pct          = 0.66   (488 / 74266)   atol 0.05
other_arrival_pooled_pct = 1.77   (1674 / 94514)  atol 0.05
shk_minus_other          = 5.32                    atol 0.05
shk_over_other_ratio     = 4.00                    atol 0.05
```
`transport_access` is the argmax of `shk_minus_other`; next-largest (`waiting_crowding`) ≈ 0.91.

**§5.4 §4.3 quadrants** (8 SEM-scored codes):
```
transport_access            → ACT NOW      priority_n=1.000  causal_opportunity=1.000
opening_hours_availability  → ACT NOW                        causal_opportunity=0.323
food_amenities_gap          → ACT NOW                        causal_opportunity=0.311
itinerary_fit_time_cost     → watch                          causal_opportunity=0.359
cleanliness_comfort         → quick win                      causal_opportunity=0.153
wayfinding_signage          → deprioritize
waiting_crowding            → deprioritize
accessibility_mobility      → deprioritize
```
Assertion that carries the thesis: `transport_access` is the **unique** ACT-NOW-corner point
at the max of both axes.

---

## 6. New ADR — `docs/adr/0006-synthesis-friction-causal-join.md`

Next in sequence after `0005-national-synthetic-control-arm.md`. Record:
- **Context:** causal arm established a transient, corridor-concentrated surge; needed a
  mechanism layer to explain fade and cap-on-conversion.
- **Decision:** join FTAS friction (Feed B/B′) + SEM nudge priority (Feed C) to the SCM
  per-municipality summary (Feed A) via exact Japanese-name match; classify regimes; lead
  with cross-municipality and cross-arrival-mode **pattern**, treating FTAS as intercept-survey
  evidence (magnitudes/rank-order, not population effects).
- **Consequence:** single dominant intervention target (transport/last-mile access) identified
  on four independent axes; `make synthesis` reproduces the tables; figures + narrative saved
  as thesis artifacts.
- **Caveats:** intercept-survey selection bias (7.09% is a floor); `市町村` = response location
  not residence; §4.1 n=13 is pattern-level, §4.2 is the load-bearing quantitative result.

---

## 7. Apply order & effort

1. Add `scripts/synthesis_friction_causal.py` (§1) — ~2h, the bulk of the work.
2. Add Makefile `synthesis` target + reproduce-submission edit (§2) — 5 min.
3. Add `tests/test_synthesis_friction_causal.py` (§3, oracles §5) — ~1h.
4. Add ADR 0006 (§6) — 20 min.
5. **Preflight — verify all four input checksums before running `make synthesis`.** The four
   input feeds are the source of truth for every oracle in §5; if any has drifted, the target
   will produce numbers that don't match §5 and the test will (correctly) fail. Run this
   **before** `make synthesis`, from the repo root:
   ```bash
   sha256sum \
     data/causal/fukui_municipalities_scm.csv \
     output/official_fukui/ftas_friction_by_municipality.csv \
     output/official_fukui/ftas_friction_by_transport_mode.csv \
     output/sem/nudge_priority_ranking.csv
   ```
   Compare each against the §4 table.
   - **All four match** → proceed to step 6.
   - **A `*_ftas_*` or `nudge_*` feed differs** → its upstream target (`build-ftas` /
     `nudge-ranking`) produced a different file. Re-run that target, then **re-derive the §5
     oracles** from the new feeds — do NOT edit a checksum or an oracle to force a pass.
   - **`fukui_municipalities_scm.csv` (Feed A) differs or is absent** → this is the one hard
     blocker. Feed A is the causal arm's committed summary, not regenerated by any target here
     (see §0). Stop and ask the team where the causal-arm summary is persisted; do not proceed.
6. Run `make build-ftas sem-ftas nudge-ranking synthesis && make test` — verify oracles pass.

The test itself (§3, assertion 5) re-checks these same four checksums at runtime, so a drift
that slips past the preflight still fails the build rather than silently shipping wrong numbers.
