# 6. From Diagnosis to Intervention

## 6.0 Purpose

Chapters 4 and 5 diagnosed *where* the friction in Fukui's inbound-tourism
experience concentrates. This chapter turns that diagnosis into a testable
intervention. The argument has a single spine: Chapter 4 establishes **where**
the friction lies, Direction C explains **why** some destinations convert a
demand shock into durable visitation while others retain only a transient bump,
and Direction B specifies **how** to test the corresponding fix. Read together
they form one causal story — a diagnosed constraint, an identified conversion
mechanism, and a pre-registered experiment — rather than three independent
analyses placed side by side. All quantities regenerate from committed
artifacts (`make synthesis durability-mechanisms causal-robustness
nudge-pilot-power`; evidence bindings in `thesis_master.md`).

## 6.1 What the diagnosis established

The friction diagnosis converges on a single dominant constraint. Splitting the
full FTAS sample by arrival mode, shinkansen arrivers report transport-access
friction at **7.09%**, against **0.66%** for car arrivers and **1.77%** pooled
across other modes — a roughly **fourfold** gap (n = 10,493 rail vs 74,266 car;
z = 51.5 vs car, z = 34.5 vs pooled). In the §4.3 priority matrix,
`transport_access` is the unique occupant of the top-right corner of the
"act now" quadrant, attaining the maximum of both axes (normalized
priority = 1.000, causal opportunity = 1.000). The structural model
concurs: in SEM Stage 2, `transport_access` is the single largest damage path to
visitor satisfaction (β ≈ −0.123, p ≈ 1.2 × 10⁻⁸). Direction D's robustness work
confirmed the demand signal these frictions gate is real, not an artifact of the
March 2024 Hokuriku Shinkansen extension: Fukui City's opening-window surge of
**+29.2%** clears a one-sided in-space placebo test at **p = 0.041** against 1,538
well-fitting donor municipalities, a backdated-2023 negative control is silent
(p = 0.47), and the well-fitting significant set (at the 10% one-sided level;
see §5.3) is exactly {Eiheiji, Fukui City, Tsuruga, Sakai}. The diagnosis is therefore well-identified and causally credible:
transport access is both the largest measured friction and the one with the
clearest opportunity for intervention.

## 6.2 The durability mechanism (Direction C)

The diagnosis says the shinkansen delivered a genuine, measurable demand shock and
that transport-access friction is the constraint most worth relieving. It does not,
by itself, explain why the shock persists in some municipalities and dissipates in
others. Direction C supplies that explanation, and the answer is counter-intuitive
enough to reorganize the intervention that follows.

Durability is a matter of **last-mile conversion** — turning a first-time arrival at
the shinkansen gate into a completed visit to a destination anchor — and **not** a
matter of repeat visitation. The municipalities whose demand shock endures
(Eiheiji, JIS 18322; Sakai, JIS 18210) are those that reliably convert new station
arrivals into anchor visits: the Eihei-ji temple complex, the Tōjinbō cliffs at
Sakai. Fukui City (JIS 18201), by contrast, captures the arrival — passengers step
off the train there — but leaks the conversion, and so records a transient bump
rather than durable growth. The mechanism is corroborated at the friction level:
across thirteen high-confidence municipalities, transport-access friction correlates
with the leaked synthetic-control lift at **r = 0.826** (Fig. 7), tying the conversion
story directly back to the constraint the diagnosis flagged.

The crucial and initially surprising observation is that **repeat-visit share
anti-predicts durability**. This is not a paradox once the mechanism is stated
correctly. Durable anchors do not run on returning visitors; they run on a steady
inflow of *new* first-timers completing the last mile. A high repeat share is a
signature of a destination that has stopped acquiring new station-to-anchor
conversions and is instead recirculating an existing base — precisely the profile
that fails to convert a fresh demand shock into sustained growth. Read this way,
`transport_access` is not merely a satisfaction complaint registered on a survey; it
is the mechanical gate on conversion. The SEM coefficient (β ≈ −0.123) and the
durability mechanism describe the same causal joint from two directions: friction at
the gate is what suppresses the conversion that durability requires.

## 6.3 The intervention (Direction B): a pre-registered pilot

Direction B is the closing move of the argument — the experiment implied by the
mechanism. It is a **design**, pre-registered and scaffolded, and not a run
experiment; no result in this section should be read as evidence of an effect. Its
value is that it makes the mechanism falsifiable.

The instrument is a five-condition, between-subjects study built on SEM-aligned
Likert constructs. Its endpoint is inverted directly off Direction C's finding: the
**primary outcome is visit-intention on the anchor task** — the station-to-anchor
conversion the mechanism identifies — rather than repeat-visit conversion, which
Direction C showed to be the wrong target. The **primary contrast is control versus
`transport_access`**, testing precisely the SEM Stage-2 mediator (β ≈ −0.123). A
three-task rotation gives within-subject coverage of both regimes: tasks set in the
transient corridor (Fukui City, JIS 18201; Awara, JIS 18208) point respondents
toward durable-regime anchors (Eiheiji, Sakai), while the existing Katsuyama (JIS
18206) museum task covers a further anchor. Assignment uses stratified block
randomization (blocks of five) on `fukui_familiarity × japan_travel_experience`,
seeded server-side — a deliberate replacement for the scaffold's original
unstratified draw.

The power plan is where the design's honesty is load-bearing, and it deserves to be
stated plainly. The observed effect size, d = 0.25, is the **car-versus-rail
transport-satisfaction gap** — a *selection* contrast between two populations, and
therefore a **ceiling** on what a nudge could achieve, not the effect a nudge should
be expected to produce. A copy-based nudge can realistically close only a fraction of
that gap, and the sample requirement is acutely sensitive to which fraction:

| Assumed true effect (d) | n per arm (80%) | across two primary arms |
|---|---|---|
| 0.25 (full ceiling) | 252 | 504 |
| 0.125 (half ceiling) | 1,005 | 2,010 |
| 0.10 | 1,570 | 3,140 |

The design meets this with a **two-stage structure**. Stage 1 is an n = 50-per-arm
online panel that, on its own, can detect only d ≥ 0.56 and is therefore explicitly
**non-confirmatory**; its deliverable is not a verdict but an **effect-size prior**
for the primary contrast, together with variance and instrument-behavior estimates.
Stage 2 is the powered confirmatory test — an on-site QR-code intercept at the Fukui,
Awara-Onsen, and Tsuruga stations, targeting actual rail arrivers, the population
whose transport-access friction is 7.09%. Stage 2's sample is set by a pre-registered
re-powering rule, **d_plan = max(0.10, d̂ − se)**, which powers the confirmatory arm
off the lower confidence bound of the stage-1 estimate rather than off the optimistic
ceiling. This sequencing is the design's answer to its own central risk: it refuses to
commit confirmatory sample against an effect size it has not yet measured.

## 6.4 Limitations and honest framing

Four limits bound the claims of this chapter. First and most important, **Direction B
is a design, not evidence** — the scaffold and pre-registration establish that the
mechanism *can* be tested, not that it *has been*. Second, the selection-ceiling logic
rests on an assumption that should be named as such: that the car–rail satisfaction gap
bounds the effect a nudge can manipulate. If the manipulable margin lies outside that
gap in either direction, the stage-2 power calculation would need revision — which is
exactly why stage 1 estimates the prior before stage 2 commits. Third, the robustness
evidence underlying the demand signal is one-sided in its significance, a deliberately
conservative posture that should be read as such. Fourth, the synthetic-control leaked
lift and its correlation with transport friction (r = 0.826) are observational; they
motivate the mechanism but do not, on their own, establish it experimentally. The
strength of the chapter is that its central claim — that the fix is testable and worth
testing — survives all four caveats intact.

## 6.5 Contribution

Taken together, the §4 → C → B arc offers a transferable template for evidence-based
regional-revitalization design: diagnose the dominant friction with survey and
structural evidence, identify the conversion mechanism that separates durable from
transient response, and specify a pre-registered experiment that tests the
mechanism at its causal joint. The Fukui case instantiates the template — transport
access as the gate, station-to-anchor conversion as the mechanism, a two-stage nudge
pilot as the test — but the pattern generalizes to any regional economy absorbing an
infrastructure-driven demand shock. It is, in the terms of this laboratory's mission,
an attempt to move from statistical diagnosis to a mechanism that can be acted on and
a behavior-change intervention that can be measured, rather than stopping at the
description of a problem.
