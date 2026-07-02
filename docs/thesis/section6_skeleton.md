# §6 — From Diagnosis to Intervention (SEEDED SKELETON)

> **Status:** skeleton seeded by the orchestration seat for Fable to expand into
> finished thesis prose. Exact numbers below are verified from committed CSVs /
> the SEM output and must be preserved byte-for-byte. `[FABLE: …]` marks prose to
> write. Do not invent figures; if a number isn't here, pull it from the cited
> artifact and cite the source.

## 6.0 Purpose of this chapter
[FABLE: 2–3 sentences. Chapters 4–5 diagnosed *where* Fukui's inbound-tourism
friction concentrates. This chapter turns diagnosis into a testable intervention.
State the spine explicitly: §4 says WHERE the friction is, Direction C says WHY
some destinations convert that friction into durable demand while others see only
a transient bump, Direction B says HOW to test the fix. A reviewer should leave
this chapter seeing one causal story, not three bolted-on analyses.]

## 6.1 What §4–§5 established (recap, one paragraph)
Verified anchors to restate, not re-derive:
- **§4.2 lead mechanism:** shinkansen arrivers report transport-access friction at
  **7.09%** vs **0.66%** car vs **1.77%** pooled-other — a **~4×** gap
  (n=10,493 rail vs 74,266 car; z=51.5 vs car, z=34.5 vs pooled).
- **§4.3 priority matrix:** `transport_access` is the **unique top-right ACT NOW**
  quadrant cell (priority_n=1.000, causal_opportunity=1.000).
- **SEM Stage-2:** `transport_access` is the #1 damage path, **β ≈ −0.123, p ≈ 1.2e-08**.
- **Robustness (Direction D):** opening-window (Mar–Apr 2024) Fukui City **+29.2%**,
  one-sided placebo **p = 0.041** vs 1,538 well-fit donors; backdated-2023 negative
  control silent (**p = 0.47**); well-fit significant set = {Eiheiji, Fukui City,
  Tsuruga, Sakai}.
[FABLE: weave these into one tight recap paragraph — the reader has seen them; this
is the springboard, not a re-report.]

## 6.2 The durability mechanism (Direction C)
Verified findings to build on:
- Durability is **anchor-last-mile / station→anchor conversion**, NOT repeat visitation.
  **Repeat-visit share *anti*-predicts durability** — this is the counter-intuitive core.
- Durable-regime anchors: **Eiheiji (JIS 18322), Sakai (18210)**. Transient: **Fukui
  City (18201)**.
- **corr(transport_access friction, leaked SCM lift) = 0.826** across 13 high-confidence
  municipalities.
- Durability outputs committed: `output/national_stats/durability_*`, `accommodation_panel.csv`.
[FABLE: this is the intellectual heart of §6. Explain the mechanism: places that
durably retain the shinkansen demand shock are the ones that convert first-time
station arrivals into completed anchor visits (Eiheiji temple, Sakai/Tojinbo), while
Fukui City captures the arrival but leaks the conversion — hence a transient bump.
Make explicit WHY repeat-share anti-predicts: durable anchors run on a steady stream
of NEW first-timers completing the last mile, not on returning visitors. Tie back to
the SEM β: transport_access isn't just a satisfaction complaint, it's the mechanical
gate on conversion.]

## 6.3 The intervention (Direction B) — a pre-registered pilot, NOT evidence
Verified design parameters (from experiments/nudge-pilot/DESIGN.md + power_analysis.md):
- Instrument: 5-condition between-subjects, SEM-aligned Likert constructs.
- **Primary endpoint:** visit-intention on the anchor task (station→anchor conversion),
  NOT repeat-visit conversion — inverted directly off C's finding.
- **Primary contrast:** control vs `transport_access` (the SEM Stage-2 β≈−0.123 mediator).
- Three-task rotation: transient corridor (Fukui City 18201, Awara 18208) pointing at
  durable anchors (Eiheiji, Sakai), plus existing Katsuyama (18206) museum task.
- Assignment: stratified block randomization (blocks of 5) on
  `fukui_familiarity × japan_travel_experience`, seeded server-side.
- **Two-stage power plan.** d=0.25 is the **observed car-vs-rail selection CEILING,
  not the expected nudge effect.** Sensitivity: d=0.25→252/arm; d=0.125 (half ceiling)
  →1,005/arm (2,010 across two primary arms); d=0.10→1,570/arm. Stage 1: n=50/arm
  online pilot (detectable only d≥0.56), **non-confirmatory**, deliverable = an
  **effect-size prior**. Stage 2: on-site QR intercept at Fukui/Awara-Onsen/Tsuruga
  stations (rail arrivers, 7.09% friction base rate); pre-registered re-power rule
  **d_plan = max(0.10, d̂ − se)**.
[FABLE: present B as the closing move of the argument AND frame it unambiguously as
pre-registered design, not a run experiment — no reader may mistake the scaffold for
a result. State the honest tension: powered to detect the full observed gap, likely
underpowered for realistic partial closure; that is WHY stage 1 estimates the prior
before stage 2 commits sample. This is disciplined future work, not a weakness.]

## 6.4 Limitations and honest framing
[FABLE: (a) B is design, not evidence; (b) selection-ceiling logic assumes the
car–rail satisfaction gap bounds the manipulable effect — state it as an assumption;
(c) one-sided significance in the robustness arm; (d) the SCM leaked-lift correlation
is observational. Keep this crisp — the strength of the chapter is that it names its
own limits.]

## 6.5 Contribution (one paragraph close)
[FABLE: what a complete §4→C→B arc contributes — a diagnosed friction, an identified
conversion mechanism, and a pre-registered test — as a transferable template for
data-driven regional-revitalization intervention design, tying back to the lab's
mission (evidence-based mechanisms that change real-world behavior).]

---
### Number provenance (do not print in final chapter; for Fable's verification)
- 7.09/0.66/1.77, z=51.5/34.5 → §4.2 mode-friction CSV (committed).
- priority_n / causal_opportunity=1.000 → §4.3 priority matrix CSV.
- β≈−0.123, p≈1.2e-08 → SEM Stage-2 output.
- +29.2%, p=0.041, p=0.47, well-fit set → robustness metrics.json / placebo CSVs.
- 0.826 → transport_access vs leaked SCM lift, 13 municipalities.
- power table → experiments/nudge-pilot/power_analysis.md.
