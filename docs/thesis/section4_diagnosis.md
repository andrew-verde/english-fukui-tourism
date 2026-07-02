# 4. Diagnosis: Where Friction Concentrates

## 4.0 Purpose

Chapter 3 established that a transport-friction shock — the March 2024 Hokuriku
Shinkansen extension — moved visitor outcomes in Fukui. That result licenses a
question it cannot answer by itself: *which* friction, experienced by *whom*,
*where*? This chapter answers it in three moves. First, it assembles the two
diagnostic inputs: a two-stage structural equation model that measures how much
each friction type damages visit intention, and a municipality-level map that
classifies where the post-extension demand response proved durable, transient,
or absent. Second, it presents the chapter's load-bearing result: splitting the
survey by arrival mode shows that transport-access friction is concentrated
almost entirely among the visitors the shinkansen itself delivers. Third, it
synthesizes both inputs into a priority × causal-opportunity matrix in which a
single friction — transport access — occupies the extreme corner on every axis.
The output of the chapter is not a list of complaints but a ranked, converging
diagnosis that Chapter 5 stress-tests and Chapter 6 turns into an intervention.

All quantities below regenerate from committed artifacts
(`make sem-ftas nudge-ranking synthesis synthesis-figures`; see
`thesis_master.md` for the full evidence bindings).

## 4.1 Diagnostic inputs: structural damage paths and demand regimes

**The structural model.** The Fukui Tourism Area Survey (FTAS) asks every
respondent — not only complainants — whether they experienced inconvenience,
which makes `reported_inconvenience` a selection-bias-free exposure. A
confirmatory factor analysis holds the three satisfaction items as a single
latent (standardized loadings 0.87 / 0.51 / 0.84 for overall, transport, and
product satisfaction). Stage 1, estimated on the full sample (n = 16,219;
CFI = 0.990, RMSEA = 0.044), gives the transmission structure: friction
depresses satisfaction (β = −0.21), satisfaction drives visit intention
(β = 0.80), and the direct friction-to-intention path is small (β = −0.06).
Roughly 73% of friction's total damage to visit intention therefore travels
*through* satisfaction — friction matters because it makes visits worse, not
because it independently deters return.

Stage 2 asks *which* friction. Among the 2,565 respondents who reported
inconvenience and left classifiable free text (CFI = 0.906, RMSEA = 0.042),
per-type damage paths to satisfaction separate sharply: `transport_access` is
the largest and most precisely estimated (β ≈ −0.123, p ≈ 1.2 × 10⁻⁸), followed
by `opening_hours_availability` (β ≈ −0.105, p ≈ 1.0 × 10⁻⁶); the remaining six
coded types are small (|β| ≤ 0.065) or statistically silent. Conditioning
Stage 2 on friction reporters is deliberate — coding non-writers as
friction-free would dilute every path toward zero. Transport access is also the
most *prevalent* coded friction, tagged in 20.3% of classifiable reports (520
of 2,565), five times the share of the next substantive categories
(opening hours 4.1%, food/amenities 4.2%).

**The regime map.** The second input joins these survey frictions to the
municipality-level demand response, classified from the synthetic-control
estimates developed in Chapter 5 (the join and regime rules are recorded in
ADR 0006; Fig. 1). Of the seventeen municipalities with joinable survey
coverage, three show a *durable* response (opening-window lift that persists),
six a *transient* one (lift that decays), and eight none; restricting to the
thirteen municipalities whose synthetic controls fit well pre-event
(high-confidence set), the counts are two durable — Eiheiji (JIS 18322,
+49.0% opening lift sustaining at +14.5%) and Sakai (18210) — versus four
transient, led by Fukui City (18201, +29.2% opening lift decaying to −11.3%,
a leaked lift of 40.5 percentage points) with Tsuruga (18202), Awara (18208),
and Sabae (18207). The map carries a dose–response signature that anticipates
the mechanism developed in Chapter 6: among high-confidence municipalities,
transport-access friction is markedly higher where the demand response leaks
(transient mean 2.86% vs 1.73% elsewhere), and friction prevalence correlates
with the leaked synthetic-control lift at r = 0.826 across the thirteen. With
n = 13 this is a pattern-level observation, not an estimate to headline — but
it is the first sign that the survey's loudest complaint and the demand data's
leakage are the same phenomenon seen twice.

## 4.2 The arrival-mode contrast

The chapter's central quantitative result comes from splitting friction
prevalence by how visitors arrived (Fig. 2). Shinkansen arrivers report
transport-access friction at **7.09%** (744 of 10,493). Private-car arrivers —
the large majority of the sample — report it at **0.66%** (488 of 74,266), and
all other visitor arrival modes pooled (airplane, local train, private and
rental car, tour bus) at **1.77%** (1,674 of 94,514). The rail-versus-pooled
gap is 5.32 percentage points, a ratio of almost exactly **four** (4.00×), and
it is not a small-sample artifact: z = 51.5 against car arrivers and z = 34.5
against the pooled contrast. Nor is it a generic rail-arriver grievance
profile: transport access is the *argmax* of the shinkansen-minus-other gap
across all twelve coded friction types, and the next-largest gap
(waiting/crowding, 0.92 pp) is smaller by a factor of almost six.

The reading is specific. The shinkansen solved the problem of *reaching Fukui*
and thereby exposed the problem of *moving within it*: rail arrivers land at a
station without a car, and the last mile to the destinations they came for is
exactly where the friction bites. Two caveats bound the number without
weakening the conclusion. FTAS is an intercept survey, so 7.09% is best read
as a floor on the underlying rate among rail arrivers (those deterred entirely
are never intercepted), and prevalences should be used for magnitude ordering
rather than population estimates. Both cut against the null, not against the
contrast.

## 4.3 The priority × causal-opportunity matrix

The final move combines everything the diagnosis has produced into a single
decision surface (Fig. 3). For the eight SEM-scored friction types, the
*priority* axis normalizes an evidence-weighted score — SEM damage path ×
prevalence × the satisfaction-to-intention transmission — and the
*causal-opportunity* axis averages three normalized signals: the arrival-mode
ratio (§4.2), the correlation of each friction's prevalence with leaked
synthetic-control lift across high-confidence municipalities (§4.1), and the
absolute SEM path. A median split on both axes yields four quadrants.

`transport_access` is the unique occupant of the top-right corner, and not
marginally: it attains the maximum of *both* axes (priority = 1.000,
causal opportunity = 1.000). Two further frictions clear the ACT-NOW quadrant
at much lower opportunity — `opening_hours_availability` (0.323) and
`food_amenities_gap` (0.314) — while `itinerary_fit_time_cost` lands in
"watch" (0.359), `cleanliness_comfort` in "quick win" (0.153), and wayfinding,
waiting/crowding, and accessibility are deprioritized. In the evidence-weighted
ranking behind the priority axis, transport access scores 0.0200 against
0.0034 for opening hours — a factor of roughly six — with everything else
below 0.0017.

The force of the matrix is convergence. Four evidentiary axes with different
failure modes — a structural damage path estimated on survey covariance, a
prevalence count, a cross-arrival-mode contrast, and a cross-municipality
correlation with an independent demand-side estimate — would not be expected
to agree if the diagnosis were an artifact of any one of them. They agree:
transport access is simultaneously the most damaging friction per report, the
most reported, the most concentrated among the visitors the new infrastructure
delivers, and the most correlated with where the demand shock fails to stick.

## 4.4 What the diagnosis does and does not establish

Three boundaries. First, the load-bearing quantitative result of this chapter
is the §4.2 arrival-mode contrast; the §4.1 regime dose–response is
deliberately presented as pattern-level corroboration (n = 13 municipalities),
and the matrix is a synthesis device, not an inferential test. Second, FTAS
records the *response location*, not residence or full itinerary, and its
intercept design means all prevalences are floors under selection — magnitudes
and rank order are trustworthy; population rates are not claimed. Third, the
diagnosis is correlational about *demand*: it shows where friction concentrates
and that this concentration co-locates with demand leakage, but it does not by
itself establish that the post-extension demand signal is real rather than an
artifact of donor choice or timing. That is Chapter 5's burden. What survives
these boundaries is the chapter's claim: every instrument this thesis can point
at the problem points at the same constraint, and the constraint is transport
access for rail arrivers — the last mile, not the trunk line.
