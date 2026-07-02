# 1. Introduction

## 1.1 Motivation: an infrastructure shock as a natural experiment

Japan's regional-revitalization policy leans heavily on a single instrument:
large transport infrastructure. The premise is that connecting a peripheral
region to the high-speed rail network converts latent demand into visitors,
and visitors into regional income. The premise is rarely tested at the level
where it succeeds or fails — the individual municipality, the individual
visitor's experience — because the counterfactual is hard and the data are
usually private. On 16 March 2024 the Hokuriku Shinkansen was extended from
Kanazawa to Tsuruga, abruptly connecting Fukui Prefecture to the network, and
Fukui's unusually rich open-data ecosystem makes the test possible: official
visitor-survey microdata spanning the opening, monthly municipal visitor
counts for the whole country, and comparison surveys in the neighboring
prefectures.

This thesis uses that conjunction to ask three questions, stated canonically
in the project's domain charter (`CONTEXT.md`): how did the extension affect
tourism outcomes in Fukui; which frictions shape satisfaction and revisit
intent; and which interventions should be prioritized. The answers turn out to
form a single causal story rather than three separate studies.

## 1.2 The argument and the chapters

The argument, in one paragraph. The extension caused a real improvement in
visitor experience — recommendation intent rose by over half a point on an
11-point scale, robust to the January 2024 Noto earthquake that contaminates
the naive comparison (Chapter 3). But diagnosis of the surviving frictions
shows the gain is gated: splitting the survey by arrival mode, the visitors
the shinkansen itself delivers report transport-access friction at four times
the rate of everyone else — the trunk line was fixed and the last mile was
not — and every diagnostic axis (structural damage paths, prevalence,
arrival-mode concentration, correlation with demand leakage) converges on the
same constraint (Chapter 4). A national synthetic control confirms the demand
surge behind this diagnosis is real, corridor-concentrated, and transient
almost everywhere it appears (Chapter 5). The transience is the key: demand
endures only where first-time station arrivals convert into completed visits
to a destination anchor, and repeat-visit share *anti*-predicts durability —
so the binding problem is station-to-anchor conversion, and the thesis closes
with a pre-registered, two-stage nudge pilot designed to test exactly that
conversion at its causal joint (Chapter 6).

Chapter 2 precedes all of this with the data and the discipline: every number
in the thesis regenerates from pinned open-data inputs via a single command
(`make reproduce-submission`), a property enforced by the test suite rather
than promised. Chapter 7 concludes with contributions, consolidated
limitations, and the path from design to field experiment.

## 1.3 Stance and scope

Three commitments shape what follows. First, *effect sizes and uncertainty,
not significance alone*: every headline estimate carries its robustness
battery, and fragile results (revisit intention in Chapter 3) are labeled
fragile rather than headlined. Second, *honest limits as structure, not
disclaimer*: each analytical chapter ends by stating what its design cannot
establish, and the intervention of Chapter 6 is presented as a pre-registered
design, explicitly not as evidence. Third, *reproducibility as method*: the
thesis is built from public open data by a pipeline whose provenance rules are
themselves tested, so a skeptical reader's path from any claim to its
generating artifact is short and mechanical. The scope is correspondingly
bounded: visitor experience and demand in one prefecture around one
infrastructure event, with generalization offered as a template (diagnose the
dominant friction, identify the conversion mechanism, pre-register the test)
rather than as an extrapolated estimate.
