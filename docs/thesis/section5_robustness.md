# 5. Robustness: Is the Demand Signal Real?

## 5.0 Purpose

Chapter 4 closed on a deliberately unpaid debt: its diagnosis shows that
transport-access friction co-locates with demand leakage, but it treats the
post-extension demand signal itself as given. This chapter pays that debt. It
first introduces the synthetic-control estimator that the §4.1 regime map
consumes — the machinery has so far been used before being explained — and then
subjects its headline estimate to the falsification tests a skeptical reader
should demand: an in-space placebo across every donor municipality in the
country, a backdated in-time negative control, and leave-one-out donor
sensitivity. The chapter's claim is narrow and load-bearing: the March 2024
opening surge is real, directionally predicted, corridor-concentrated, and not
an artifact of donor choice or timing. All quantities regenerate from committed
artifacts (`make synth-causal-arm causal-robustness robustness-figures
gap-trajectories`; evidence bindings in `thesis_master.md`, design decisions in
ADR 0005).

## 5.1 The estimator: a national synthetic control

The obvious causal design — the Ishikawa/Toyama difference-in-differences of
Chapter 3 — has a compromised control: the January 2024 Noto Peninsula
earthquake struck Ishikawa two months before the extension opened, injecting a
large, simultaneous, opposite-signed tourism shock into the comparison. The
primary counterfactual therefore comes from a synthetic-control design instead
(ADR 0005), with the DiD retained as a secondary check.

The data are the commit-pinned `code4fukui/japan-kanko-stat` panel: monthly
municipal tourist-visitor counts (観光来訪者数) for all 47 prefectures,
January 2021 through December 2025 — 60 months, of which 38 precede the event
month (EVENT_YM = 202403). The counts are mobile-location-derived vendor
estimates rather than a census, so the arm supports relative and gap inference,
never absolute headcounts; the outcome is log-transformed throughout. The donor
pool excludes the four Hokuriku-line-affected prefectures (Niigata, Toyama,
Ishikawa, Fukui), since they share the treatment; what remains after dropping
any municipality with a coverage gap is **1,709 donor municipalities** with
full 60-month coverage. For each treated Fukui municipality, an Abadie
synthetic control — convex donor weights minimizing pre-period root mean
squared prediction error, fit by a deterministic Frank–Wolfe solver with no
randomness — produces a counterfactual trajectory, and the estimate is the
treated-minus-synthetic gap. Fit quality is policed, not assumed: a unit counts
as well fit only if its pre-period RMSPE is at most 0.15 in log units. Fukui
City (JIS 18201), the primary treated unit, fits tightly at 0.052.

## 5.2 The shape of the effect disciplines the test statistic

The estimand must match the effect's shape. The §4.1 regime map already showed
that outside two anchor municipalities the post-extension lift *decays*; for
such a transient effect, the conventional post-period-mean gap statistic
averages the surge away and understates a real effect. Fukui City illustrates
the point exactly: its opening surge is large, but its post-mean gap is
statistically indistinguishable from zero (two-sided placebo p = 0.83) —
a *correct* description of a spike that faded, and a useless test of whether
the spike happened. The falsification battery therefore targets the **opening
window** — March–April 2024, the first two post-event months — where the
extension's effect, if real, must appear (Fig. 6 shows the full gap
trajectories that motivate this choice).

## 5.3 In-space placebo: the surge against a national null

The in-space placebo fits every donor municipality as if it, too, had been
treated in March 2024, building the null distribution of opening-window gaps
that pure noise plus model error generates. Donors whose synthetic controls fit
worse than five times the treated unit's pre-RMSPE are dropped from the null
(RMSPE_FIT_MULT = 5.0), which for Fukui City leaves **1,538** well-fitting
placebos. Against that null (Fig. 4), Fukui City's opening surge of **+29.2%** sits at a
one-sided p = **0.041**: fewer than one in twenty-four donor municipalities
anywhere in the country produced an opening gap that large by chance. The test
is one-sided by design — the Shinkansen predicts a directional increase, and
the surge's sign was specified by the intervention, not discovered in the data
— but the two-sided value (p = 0.168) is reported for completeness, and §6.4
carries this posture forward as an explicit limitation rather than a footnote.

The heterogeneity is as informative as the headline. Among well-fitting treated
municipalities, four clear the 10% one-sided level: Eiheiji (JIS 18322, +49.0%,
p = 0.025), Fukui City (p = 0.041), Tsuruga (18202, +22.0%, p = 0.077), and
Sakai (18210, +18.1%, p = 0.096), with Eiheiji and Fukui City also clearing 5%.
This is precisely the new-corridor geography — the terminal city, the two other
new-station municipalities' catchments, and the temple anchor one valley over —
and it is the same set the regime map classifies as durable or transient
responders. Two large spikes are deliberately *excluded* from the significant
set by the fit gate: Katsuyama (18206, +58.5%) and Ikeda (18382, +48.0%) fail
the pre-fit criterion (pre-RMSPE 0.30 and 0.30 against the 0.15 bar), and their
estimates are reported only as low-confidence in the regime map. A robustness
battery that discards its two most spectacular point estimates for fit reasons
is behaving as designed.

## 5.4 Negative control and donor sensitivity

**Backdated in-time placebo.** If the estimator manufactures surges, it should
manufacture one anywhere. Re-running the full design with the event moved to
March 2023 (INTIME_EVENT_YM = 202303), using only genuinely pre-event data,
Fukui City's backdated opening "surge" is −3.5% with a one-sided p = **0.47**
against 1,544 well-fitting placebos — silent, as a real 2024 effect requires
(Fig. 5).

**Leave-one-out donors.** Dropping each of the 24 positive-weight donors from
Fukui City's synthetic control in turn and refitting, the opening surge ranges
from **26.2% to 39.8%** — never approaching zero, never dependent on any single
donor. The +29.2% headline is a property of the donor pool, not of a lucky
weight on one municipality.

## 5.5 What survives

The demand signal that Chapters 4 and 6 build on is real by every test this
design can throw at it: a national in-space placebo (p = 0.041, one-sided, with
the two-sided value disclosed), a silent backdated negative control (p = 0.47),
donor-robustness bounded well away from zero, and a significant set whose
geography matches the new corridor rather than scattering at random. Its limits
are equally clear: the inference is one-sided by pre-specification; the panel
supports gaps, not levels; and the surge is *transient* almost everywhere it
appears — which is not a weakness of the causal claim but the very fact the
thesis turns on. Why the same shock endures in Eiheiji and Sakai and leaks away
in Fukui City is not a question robustness machinery can answer. That question
— the durability mechanism, and the intervention it implies — is Chapter 6's.
