# 3. Impact: The Shinkansen Extension as a Friction Shock

## 3.0 Purpose

Everything that follows in this thesis rests on a single historical event: on
16 March 2024, the Hokuriku Shinkansen was extended from Kanazawa to Tsuruga,
abruptly cutting the cost of reaching Fukui by rail. This chapter asks the
first causal question that event permits: did reducing transport friction move
what visitors *experienced*? It estimates difference-in-differences effects on
four identically-worded survey outcomes and finds a specific pattern — a large,
robust gain in net promoter score and a small, robust gain in transport
satisfaction, against a null placebo-style outcome and a revisit-intention
effect that does not survive scrutiny. The chapter also establishes, honestly,
why its own control is imperfect (the January 2024 Noto Peninsula earthquake),
which is precisely why the *demand-volume* causal claim is carried by the
national synthetic control of Chapter 5 rather than by this design (ADR 0005).
Chapter 3's estimand — experience quality — and Chapter 5's — visitor volume —
are complements, not substitutes. All quantities regenerate from
`make hokuriku-did-event-study` (evidence bindings in `thesis_master.md`).

## 3.1 Data and design

The data are the Hokuriku inbound-tourism consortium's merged survey microdata
(CC-BY 4.0; upstream: Fukui FTAS, CC-BY 4.0, and the Ishikawa QR survey,
CC-BY 2.1 JP), 103,807 responses spanning April 2023 through June 2026. Fukui
is the treated prefecture and Ishikawa the control; Toyama appears in the
merged file only from 2025 and is excluded for lack of a pre-period. Because
the two prefectures field different instruments, only the four outcomes with
verified identical wording are used: transport satisfaction, product/service
satisfaction, net promoter score (0–10), and revisit intention (the
satisfaction items on 1–5 scales). Estimates are treated × post OLS with
prefecture × month clustered standard errors (73 clusters; 67 in specifications
that drop months); the accompanying event study uses HC1 errors, since
clustering degenerates with two clusters per month, and takes February 2024 —
the last pre-opening month — as reference. Levels differ across prefectures
(pre-period NPS: Fukui 7.48, Ishikawa 8.40); the design identifies changes
against those fixed gaps, not the gaps themselves.

## 3.2 Results: what moved, what did not

Across five specifications — baseline; composition controls (gender, age band,
local residency); dropping January–March 2024; dropping Noto-area responses;
and both earthquake mitigations together — the pattern is stable:

| Outcome | Baseline | Earthquake-robust* | Verdict |
|---|---|---|---|
| NPS (0–10) | **+0.55** (p ≈ 1.5 × 10⁻²⁷) | **+0.65** | robust; grows under robustness |
| Transport satisfaction (1–5) | **+0.055** (p = 0.024) | **+0.077** | robust |
| Revisit intention (1–5) | +0.038 (p = 0.11) | +0.008 (p = 0.66) | fragile — not headlined |
| Product/service satisfaction (1–5) | −0.037 (p = 0.31) | −0.017 (p = 0.74) | null (placebo-style) |

\* the combined drop-January–March-2024 + drop-Noto-sites specification.

The internal logic of the pattern matters more than any single coefficient.
The two outcomes a transport intervention *should* move — willingness to
recommend, and satisfaction with transport itself — move, and both strengthen
when the earthquake-contaminated observations are removed. The outcome it
should *not* move — satisfaction with products and services, which the
extension did nothing to change — stays null in every specification, behaving
as an in-design placebo. And revisit intention, the outcome a naive
tourism-promotion reading would headline, shrinks from a marginal +0.038 to
+0.008 once the earthquake mitigations are applied. That fragility is worth
holding onto: it is the first evidence in this thesis that *repeat visitation
is the wrong margin to build on* — a hint that Chapter 6's durability
mechanism, where repeat-visit share anti-predicts durable growth, later
explains rather than explains away.

## 3.3 Threats to identification

Four threats, stated plainly. **First, the Noto earthquake** (1 January 2024)
struck the control prefecture ten weeks before treatment — the single largest
threat to this design. Both mitigations (dropping January–March 2024; dropping
Noto-area control sites) and their combination *raise* the NPS and
transport-satisfaction estimates, indicating the contamination biases the
baseline toward zero rather than manufacturing the result. It cannot be fully
excised, which is why ADR 0005 assigns the headline demand estimate to a donor
pool that excludes Hokuriku entirely (Chapter 5). **Second, pre-trends are
imperfect:** 6 of 20 pre-reference event-study coefficients are significant at
the 5% level — at n ≈ 104,000, trivial fluctuations are precisely estimated.
The pre-period coefficients are mixed-sign, with all but one inside ±0.28 and
the largest (−0.52) in the sparse earliest common month (September 2023);
effect magnitudes should be read against that wobble, and the NPS estimate is
larger than every pre-period coefficient and grows under robustness. **Third,
rows are responses, not respondents:** the public file anonymizes member IDs,
and the local FTAS extract indicates roughly 47% of Fukui rows are repeat
responses, so unclustered errors would be anti-conservative; the prefecture ×
month clustering mitigates but cannot fully remove this dependence. **Fourth,
composition:** the Shinkansen changes who visits, and for surveyed visitors
that shift is part of the treatment effect, not a confound — the
composition-controls specification (which barely moves any estimate) adjusts
for demographics, but origin-mix change is retained deliberately as part of
what the extension did. A residual measurement note: transport satisfaction
has ~50% item response, so its (small, robust) coefficient rests on the
subsample answering that item.

## 3.4 What the impact estimate establishes

A transport-friction shock caused a real improvement in the visitor
experience: recommendation intent rose by over half a point on an 11-point
scale, transport satisfaction rose by a small but robust margin, a placebo
outcome stayed flat, and the pattern strengthens as earthquake contamination
is removed. Two questions are deliberately left open. *Whether the shock also
moved visitor volume* — and whether that movement was real rather than
post-COVID recovery — is Chapter 5's question, answered with an uncontaminated
national donor pool. *Why the experience gain concentrates where it does, and
what friction still binds* is Chapter 4's, answered by splitting the same
survey by arrival mode. The event-study trajectory and parallel-trends
diagnostics are shown in Figs. 8–9, with the full specification table in
`output/hokuriku_merged/did_event_study_report.md`.
