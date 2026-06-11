# Results Overview — Friction Impact and Nudge Design for Fukui Tourism

One-page map of the thesis's quantitative arc. All numbers regenerate from the
Makefile targets named in each section; decisions are recorded in
`docs/adr/0001` and `docs/adr/0002`, terminology in `CONTEXT.md`.

## The arc

```
IMPACT          MECHANISM            INTERVENTION
Shinkansen DiD  →  Two-stage SEM  →  Nudge priority ranking → nudge-pilot app
(causal shock)     (transmission)     (evidence-weighted)      (built artifact)
```

## 1. Impact: a transport-friction shock moves outcomes (DiD)

`make hokuriku-did-event-study` — Fukui (treated) vs Ishikawa (control) around
the March 2024 Hokuriku Shinkansen extension; merged tri-prefecture microdata
(n≈104k responses, Apr 2023–present, CC-BY); prefecture×month clustered SEs.

| Outcome | DiD (baseline) | Earthquake-robust* | Verdict |
|---|---|---|---|
| NPS (0–10) | +0.55 | +0.65 | robust, grows under robustness |
| Transport satisfaction (1–5) | +0.05 | +0.08 | robust |
| Revisit intention (1–5) | +0.04 | +0.01 | fragile — do not headline |
| Product/service satisfaction | −0.04 | −0.02 | null (placebo-style check) |

*drop Jan–Mar 2024 + Noto-area control sites. Event-study plot and pre-trend
diagnostics in `output/hokuriku_merged/did_event_study_report.md`. Pre-trends
are imperfect (6/20 pre-coefficients significant at huge n); report effect
magnitudes against the ±0.1–0.4 mixed-sign pre-wobble.

## 2. Mechanism: friction transmits to intention via satisfaction (SEM)

`make sem-ftas` — deduplicated FTAS respondents; exposure =
`reported_inconvenience` (asked of everyone — selection-bias-free).

- CFA: the three satisfaction items hold as one latent (loadings .87/.53/.86).
- Stage 1 (n=15,776; CFI .990, RMSEA .044):
  friction → satisfaction **β = −0.21**; satisfaction → intention **β = 0.80**;
  direct friction → intention β = −0.06 → **~72% of friction's damage to visit
  intention is mediated through satisfaction.**
- Stage 2 (n=2,503 friction reporters with free text; CFI .91): friction-type
  paths ranked below. Conditioning on reporters avoids coding non-writers as
  friction-free.

## 3. Intervention: evidence-weighted nudge ranking

`make nudge-ranking` — priority = path × prevalence × (satisfaction→intention).

| # | Friction | SEM path | Prevalence | Priority |
|---|----------|----------|------------|----------|
| 1 | Transport / Access | −0.124 | 20.4% | 0.0202 |
| 2 | Opening Hours / Availability | −0.107 | 4.2% | 0.0036 |
| 3 | Cleanliness / Comfort | −0.049 | 3.4% | 0.0013 |

Transport/access dominates by ~6× — coherent with the DiD: the one historical
friction-reduction shock we can observe (Shinkansen) was a transport
intervention, and it moved NPS. Intervention candidates per code in
`output/sem/nudge_priority_ranking.md`; delivery vehicle =
`experiments/nudge-pilot/` (artifact only, ADR 0002).

## 4. Measurement validity (in progress)

`make gold-set` / `make gold-set-eval` — 300 blind, stratified free-text
snippets await two native-speaker coders; outputs Cohen's κ and per-code
precision/recall with Wilson CIs. Until then, friction-tag results carry a
"keyword tagger, unvalidated" caveat.

## Supporting layers

- English Google reviews (n=915): exploratory inbound-perception signal only;
  side-project scope. Corrected SR results in `output/statistical_summary.md`.
- Statistical integrity: the 2026-06 audit fixes (dedup, text-writer
  denominators, reported_inconvenience recode) are locked in by regression
  tests (`tests/test_statistical_validation_official.py`) and CI.
