# 7. Conclusion

## 7.1 What was established

Four findings, each carried by a different design, together answer the
thesis question. The Hokuriku Shinkansen extension *worked* as an experience
intervention: net promoter score rose +0.55 (strengthening to +0.65 once the
Noto earthquake's contamination of the control is removed) alongside a small,
robust gain in transport satisfaction, while a placebo-style outcome stayed
null (Chapter 3). The demand surge behind it was *real but mostly transient*:
Fukui City's opening-window lift of +29.2% clears a national in-space placebo
test (one-sided p = 0.041 against 1,538 well-fitting donors), survives a
backdated negative control and leave-one-out donor sensitivity, and appears
precisely along the new corridor — yet decays everywhere except the two
municipalities with strong destination anchors (Chapter 5). The binding
constraint on converting the surge is *transport-access friction among the
very visitors the extension delivers*: 7.09% of shinkansen arrivers report it,
against 0.66% of car arrivers, and it is simultaneously the largest structural
damage path to satisfaction (β ≈ −0.123), the most prevalent coded friction,
and the friction most correlated with demand leakage (Chapter 4). And the
mechanism that separates durable from transient response is *station-to-anchor
conversion, not repeat visitation* — repeat-visit share anti-predicts
durability — which inverts the natural target of tourism promotion and fixes
the endpoint of any intervention worth running (Chapter 6). All quantities
regenerate from the committed pipeline (`make reproduce-submission`; evidence
bindings in `thesis_master.md`).

## 7.2 Contributions

The thesis offers three. **Empirically**, it provides causal estimates of an
infrastructure shock on both experience and demand margins for one prefecture,
at municipal grain, from open data — including the finding that the shock's
demand effect is transient by default and durable only under an identifiable
conversion condition. **Mechanistically**, it identifies and triangulates a
single dominant friction and shows that the survey's loudest complaint and the
demand data's leakage are the same phenomenon seen from two directions,
culminating in a falsifiable conversion mechanism with a pre-registered test
design. **Methodologically**, it demonstrates a reproducibility discipline in
which provenance rules are enforced by the test suite — pinned vintages,
checksum gates, a source ledger, and a guard that fails the build when a
document makes a statistical claim without naming its reproduction path. The
combination is a transferable template for evidence-based regional
revitalization: diagnose the dominant friction, identify the conversion
mechanism, and pre-register the experiment that tests the fix at its causal
joint.

## 7.3 Consolidated limitations

The chapter-level caveats consolidate into four. The experience estimates
(Chapter 3) rest on an earthquake-compromised control mitigated, not cured, by
specification choices, with imperfect pre-trends read against a stated wobble.
The demand estimates (Chapter 5) are one-sided by pre-specification, built on
mobile-derived vendor counts that support gaps rather than levels. The
diagnosis (Chapter 4) is intercept-survey evidence — prevalences are floors,
locations are response sites, magnitudes and rank order are the trustworthy
objects — and its dose–response corroboration is pattern-level (n = 13). And
the intervention (Chapter 6) is a design: the selection ceiling d = 0.25
bounds what a nudge could achieve only under a named assumption, and no claim
of efficacy exists until the pilot runs. None of these limits undermines the
central diagnosis; all of them discipline what may be said next.

## 7.4 From design to field

The immediate next step is executing the two-stage pilot: Stage 1 (n = 50 per
arm, online, explicitly non-confirmatory) to estimate the effect-size prior,
then Stage 2 re-powered by the pre-registered rule d_plan = max(0.10, d̂ − se)
as an on-site QR intercept at the Fukui, Awara-Onsen, and Tsuruga stations.
The design's own feasibility flag stays live: if the nudge closes about half
the observed ceiling, Stage 2 requires on the order of a thousand respondents
per arm, which the 7.09%-friction rail-arriver base may not supply at
intercept rates — an argument for DMO partnership rather than against the
test. Beyond the pilot, two extensions follow naturally: archival deposit of
the replication package under a DOI (Chapter 2's publication rule), and
repetition of the template on the next corridor opening, where the diagnosis
machinery — not the Fukui-specific estimates — is the exportable object. The
thesis ends where the mission it serves points: past the statistical
description of a problem, at a mechanism that can be acted on and an
intervention that can be measured.
