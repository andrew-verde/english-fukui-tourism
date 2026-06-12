# Methods Appendix — Statistical Traceability

Companion to the code: one section per analysis, mapping **research question →
test choice → assumptions → configuration → caveats**, with file references.
Inline comments in each script carry the same reasoning at the exact code site;
this document is the cross-cutting index. Decisions: `docs/adr/0001`, `0002`.
Terminology: `CONTEXT.md`. Headline numbers: `docs/results_overview.md`.

---

## A. Data preparation (src/official_fukui/ftas.py)

| Choice | Rationale |
|---|---|
| Dedup to first response per 会員ID | FTAS's rice-bag incentive produces repeat submissions: 95,422 rows ↔ 50,285 unique members. All tests assume independent observations. Earliest response kept (deterministic; least incentive-gaming). Scoped per survey system in combined data because IDs are not global. (`scripts/statistical_validation_official.py::_dedup_respondents`) |
| `reported_inconvenience` = 感じた and not 感じなかった (or あり/有り) | The 不便さ item is an explicit felt/not-felt question, **not** a checkbox. The generic checkbox normalizer (any non-empty string → True) coded 感じなかった as True, producing a 99.99% positive rate; the true rate is 13.6%. Regression-tested. |
| `future_visit_intent_score` maps the 行きたい scale | Survey labels are また行きたい（1年以内）=5 … 行きたくない=1 (full-width １ variant included). 福井県在住 (residents) deliberately → NaN: revisit intention is undefined for locals. An earlier agree-scale map matched zero rows — the column was silently 100% empty. Regression-tested. |
| Satisfaction scores: とても満足=5 … とても不満=1; 普通 = どちらでもない = 3 | Different survey vintages use different neutral labels. |
| `friction_source_text` = 6 free-text fields concatenated | A complaint counts regardless of which box it was typed in. Per-field response rates run ~10–22%. |
| Substring (not word-boundary) keyword matching for Japanese | Japanese has no word delimiters; keywords are stems (バスが少な matches 少ない/少なく/少なかった). |

## B. English-review tests (scripts/statistical_validation.py)

**Unit:** one review. Reviews treated as independent (possible POI/reviewer
clustering is a stated limitation — these tests are exploratory).

| Test | Question | Why this test | Key configuration |
|---|---|---|---|
| SR-01a χ² goodness-of-fit | Are Fukui's themed reviews evenly spread across 5 themes? | One categorical variable vs a reference distribution. Uniform = neutral exploratory benchmark, **not** an empirical expectation. | Cramér's V on a GoF is a convention; flagged as such. |
| SR-01b/c χ² independence + permutation | Does theme mix differ by city? | Standard 2-cat association test; expected counts are sparse (<5), so the asymptotic p is supplemented by a **conditional permutation test** (theme labels shuffled against fixed city labels → both margins preserved; valid regardless of expected counts). | 10,000 permutations; p = (exceed+1)/(valid+1) (Phipson & Smyth 2010); per-test RNG streams via CRC32 offsets of seed 42 so Monte-Carlo error is independent across tests yet reproducible. Asymptotic result *suppressed* when expected_min < 1.0 (5× violation); permutation p still reported. |
| Cell diagnostics | Which cells drive the association? | **Haberman adjusted standardized residuals** ≈ N(0,1) → comparable to ±1.96. Plain Pearson residuals (variance < 1) also stored but flagged not-z-comparable. Bias-corrected Cramér's V (Bergsma 2013) reported alongside the classic V. |
| SR-02 ANOVA + Kruskal-Wallis | Does emotional intensity differ by theme? | Outcome = abs(VADER compound) — a magnitude proxy, not affective depth. Shapiro-Wilk: 5/5 theme groups non-normal → KW as the rank-based check; ε² = (H−k+1)/(n−k) (Tomczak & Tomczak 2014); Tukey-Kramer for unequal n; Brown-Forsythe (median Levene) for variance. |
| SR-05 Welch t-tests | Does mean sentiment differ by city? | Welch over Student: unequal city n and variances. **Welch-consistent Cohen's d** (denominator √((s²ₐ+s²ᵦ)/2)) matches the test's no-pooling assumption; pooled d kept for comparability. Bonferroni: adjusted p = min(3p, 1) compared to α=0.05 (never also against 0.0167 — that double-corrects). |
| Spearman ρ rating↔sentiment | Is VADER a meaningful companion to stars? | Ordinal × skewed-continuous → monotonic rank association; bootstrap CIs per city. |
| Review length KW + Mann-Whitney | Style differences by city | BH FDR across pairs; Cliff's δ = 2U/(n₁n₂) − 1 as signed effect size. |

## C. Official-survey tests (scripts/statistical_validation_official.py)

**Unit:** one deduplicated respondent (§A).

- **Friction-rate denominator.** Friction tags exist only where free text was
  written, and free-text response rates differ by instrument: Fukui ≈42%,
  Ishikawa ≈99.9%. All-respondent rates therefore measure questionnaire format
  — they *reversed the direction* of the headline comparison. All cross-
  prefecture friction tests condition on text-writers. Caveat: conditioned
  rates describe friction *among reporters*, not population prevalence.
- **Two-exposure design** (mirrors ADR 0001): primary exposure
  `reported_inconvenience` (asked of everyone — no selection bias); secondary
  exposure tagged `any_friction` *among text-writers* (never coding non-writers
  as friction-free).
- **Mann-Whitney everywhere ordinal** (5-point satisfaction, 0–10 NPS), with
  rank-biserial r and mean differences: at n≈50k all p-values vanish; effect
  magnitudes are the result. Effect directions are computed, never asserted.
- **Multiplicity:** BH FDR within each hypothesis family (12 friction codes;
  7 transport modes) per the FDR family logic.
- **Reservation pre/post test** retained as descriptive context only —
  autumn/winter pre vs spring/summer post confounds seasonality; superseded by
  the DiD (§D).
- `p = 0.0` underflow clamped to float-tiny so stored provenance distinguishes
  "vanishingly small" from "coding error".

## D. Shinkansen difference-in-differences (scripts/hokuriku_did_event_study.py)

**Identification.** The March 16, 2024 Kanazawa–Tsuruga extension is an
exogenous transport-friction-reduction shock. Fukui = treated; Ishikawa =
control (Shinkansen since 2015). Toyama excluded: enters the merged data only
in 2025 — no pre-period. Outcomes limited to identically-worded items in both
instruments: 交通の満足度, 満足度（商品・サービス）, おすすめ度 (NPS),
再訪意向 (residents excluded). Product/service satisfaction doubles as a
**placebo-style outcome** — no mechanism connects transport friction to it, so
its null supports specification validity.

**Inference.** 2×2 DiD specs cluster SEs at prefecture×month (treatment varies
at that level; 67–73 clusters). The event study uses HC1 instead: each
treated×month coefficient is identified within exactly two clusters, where
cluster covariance degenerates to zero-width CIs (observed, documented).
Reference month 2024-02 = last full pre-treatment month; months kept only when
observed in both prefectures.

**Robustness battery.** (1) composition controls — gender, harmonized age band
(Fukui stores decades 50代, Ishikawa birth years → decades), local-resident
flag — because the Shinkansen changes *who* visits; controlled and uncontrolled
specs both reported since composition shift is partly the treatment effect.
(2) Drop Jan–Mar 2024 (Noto earthquake hit the control prefecture on
2024-01-01 + opening transition). (3) Drop Noto-area response sites by
facility-name pattern. The earthquake depresses the control and would inflate
the DiD; estimates **growing** when earthquake-affected data is removed argues
the net bias runs the other way. Pre-trends: 6/20 pre-reference coefficients
significant (huge-n sensitivity); effect magnitudes are reported against the
±0.1–0.4 mixed-sign pre-wobble.

**Independence caveat.** The public merged file anonymizes 会員ID, so rows are
responses, not respondents (~47% repeat rate in the local FTAS extract);
clustering mitigates, and a dedup sensitivity on the Fukui arm is specified
thesis work.

## E. Two-stage SEM (scripts/sem_ftas.py)

**Stage 0 — CFA go/no-go.** Three indicators → just-identified (df=0; fit
indices uninformative), so the verdict rests on standardized loadings ≥ 0.4
(conventional salience). Result: .87 / .53 / .86 — latent retained; the
documented fallback (observed-mediator path model) was not needed.

**Stage 1 — full sample (n=15,776).** friction (reported_inconvenience) →
SATISFACTION (latent: overall/transport/product-service) → INTENTION (latent:
revisit + NPS), plus the direct friction→intention path. Indicators
standardized (paths in SD units per exposure); binary exposure left raw.
5-point ordinal items estimated as continuous under ML — defensible with ≥5
categories at large n (Rhemtulla et al. 2012); WLSMV noted as stricter
robustness. Fit: CFI .990, TLI .980, RMSEA .044 (Hu & Bentler 1999 thresholds).
Result: β(friction→sat) = −0.21, β(sat→intent) = 0.80, direct = −0.06 → ~72%
of friction's intention damage is mediated through satisfaction.

**Stage 2 — friction reporters with text (n=2,503).** Friction-type dummies →
SATISFACTION, conditioning on reporters because tags are only meaningful where
text exists (coding non-writers friction-free would correlate measurement error
with the outcome). Codes with <30 tagged reporters excluded (estimates
otherwise dominated by a handful of cases). Fit: CFI .906, RMSEA .042.

## F. Nudge priority ranking (scripts/rank_nudge_priorities.py)

`priority = (−min(path, 0)) × prevalence × |sat→intent path|` — the expected
SD-units of visit-intention damage a friction code transmits per friction
reporter, i.e. the **ceiling** a perfectly effective nudge could recover.
Prevalence multiplies because a rare-but-damaging friction matters less in
aggregate than a common moderate one; the mediation path multiplies because
damage reaches intention via satisfaction. Non-negative paths score zero.
Intervention candidates joined from `config/nudge_mapping.yaml`.

## G. Tagger validation (scripts/build_gold_set.py, evaluate_gold_set.py)

Every friction result inherits the keyword tagger's validity, so the tagger is
evaluated, not assumed. Gold set: 300 stratified snippets (15 per code for
precision; 120 untagged probes for false negatives), **blind** (machine tags
and strata hidden, rows shuffled) to prevent anchoring. Two native-speaker
coders → per-code Cohen's κ (chance-corrected; per-code because marginal
prevalence varies wildly); consensus rows form the gold standard; disagreements
exported for adjudication. Tagger scored per-code precision/recall/F1 with
**Wilson score intervals** (Wald degenerates at small n, p near 0/1) and an
`indicative_only` flag below 20 evaluable instances. Recall is stratum-scoped;
corpus recall requires prevalence weighting.

## H. Known limitations (cross-cutting)

1. Domestic Japanese respondents only — inbound claims rest on the exploratory
   English-review layer and are labeled as such.
2. Keyword tagging precision/recall pending the gold-set results (§G).
3. Ordinal-as-continuous ML estimation in SEM (§E); WLSMV robustness open.
4. DiD pre-trends imperfect at huge n; repeat-responder dependence in the
   merged file (§D).
5. Self-selection into free text bounds all Stage 2 / cross-prefecture friction
   statements to the reporter population (§C).

## I. Provenance and reporting integrity

**AI-assisted prose vs code-derived findings.** Every quantitative claim in
this thesis is code-derived: it regenerates from a Makefile target and is
traced in `docs/source_ledger.md` (number → command → script → input →
artifact). Prose — framing, literature connections, interpretation — was
drafted with AI assistance and reviewed by the author; it never originates
numbers. The dividing rule: if a sentence contains a number, the number must
have a ledger row; if it cannot, it is labeled **estimated** or **hypothesis**
per the ledger's status vocabulary (verified / simulated-demo / estimated /
hypothesis).

**Guards.** `tests/test_report_provenance.py` fails CI when a document in
`docs/` claims significance without naming a reproduction path, and when the
source ledger drops a primary analysis. `make data-manifest` records row
counts, schemas, and hashes for every key dataset (`output/data_manifest.*`)
so results audit without sharing row-level data. Scrape checkpoints are
backup-protected: `scripts/checkpoint_guard.py` refuses empty or sharply
smaller overwrites (override requires `FUKUI_ALLOW_SHRINK=1`).

**Demo-data quarantine.** Anything generated from scaffold/placeholder data
(currently the Chinese social media layer) is marked **simulated/demo** in the
ledger and may not be cited as an empirical finding in advisor-facing
documents.
