# Nudge Pilot Design — Station-to-Anchor Last-Mile Conversion

Status: design approved 2026-07-02; instrument changes pending implementation.
Companion to ADR 0006 and the durability-mechanism analysis
(`output/synthesis/durability_mechanisms.md`).

## Motivation

The causal arm shows the Shinkansen opening produced a transient visitor surge
in the corridor (Fukui City 18201, Tsuruga 18202, Awara 18208): an
opening-quarter spike gone within one quarter. The durable-regime
municipalities (Eiheiji 18322, Sakai 18210) instead show a delayed ramp that
plateaus — and the mechanism analysis attributes this to **new-audience
acquisition at anchor attractions**, not visitor loyalty: the durable pool has
*lower* repeat-visit share than the transient pool (50.2% vs 57.4%,
z = −14.5), no overnight advantage, and is distinguished by car-dominant
access (71.0% vs 62.3%, z = +18.2) plus an anchor attraction (Eiheiji temple,
Tojinbo/Maruoka in Sakai).

The pilot therefore tests the conversion the corridor is failing at:
**turning a rail arrival into a committed station→anchor last-mile plan.**
Rail arrivers report transport-access friction at 7.09% vs 0.66% for car
(≈4×, n = 10,493 rail; z = 51.5), and transport_access is the dominant SEM
Stage 2 damage (β ≈ −0.123, p ≈ 1.2e−08). The lever is not repeat conversion
— repeat share anti-predicts durability — but **first-visit anchor
conversion**.

## Design

Between-subjects information experiment, browser instrument in this
directory. Five conditions (unchanged IDs): `control`, `transport_access`,
`opening_hours_availability`, `itinerary_fit_time_cost`, `combined`.

**Primary contrast:** `control` vs `transport_access`. This is the
SEM-aligned contrast: the nudge supplies concrete station→anchor last-mile
information (route, frequency, transfer, last-return time). All other
contrasts are secondary.

**Primary endpoint:** visit-intention composite (3 items, mean) on the anchor
tasks. **Pre-registered mediator:** perceived-friction composite — the pilot
analogue of the SEM friction→outcome path. Secondary endpoints: planning
confidence, decision commitment (task decision option), accuracy item.

**Tasks (three, rotated):** each participant completes two of three
station→anchor tasks, covering the transient corridor pointing at anchor
destinations:

1. `eiheiji_half_day` — Fukui Station → Eiheiji Temple (transient node →
   durable anchor).
2. `tojinbo_awara` — Awara-Onsen Station → Tojinbo Cliffs (transient node →
   durable-regime Sakai anchor).
3. `museum_arrival` — Fukui Station → Dinosaur Museum, Katsuyama (transient
   node → anchor in the low-confidence durable municipality).

Task pairs and order are counterbalanced across the six ordered pairs,
assigned deterministically from the session id. Stimulus transit facts
(bus durations, frequencies) are approximate and **must be verified against
current timetables before fielding**.

**Assignment:** stratified block randomization, blocks of 5, strata =
`fukui_familiarity` × `japan_travel_experience` (both collected before the
first task). Server-side counter (Vercel API + Supabase) issues positions in
a per-stratum permuted block; static/local mode falls back to a
stratum-seeded deterministic hash (marginal balance only — acceptable for
stage 1 dry runs, not for confirmatory analysis). The nudge panel header is
neutral ("Planning notes") so the condition label is never shown to
participants.

## Power and the two-stage plan

**The d = 0.25 anchor is a selection ceiling, not an expected effect.** The
corridor's observed car-vs-rail gap in FTAS transport-satisfaction is
d ≈ 0.25 pooled-SD (car 4.31 vs rail 4.11, SD ≈ 0.74–0.84, n ≈ 8,800
scored). That gap reflects self-selection of mode as well as the friction a
nudge could remove; it bounds from above what an information nudge can close.
A nudge that closes half the gap (d ≈ 0.125) is the honest planning case.

n per arm at α = 0.05 two-sided, power 0.80 (two-sample means,
n = 2(z₀.₉₇₅+z₀.₈₀)²/d²):

| d | n/arm | primary contrast (2 arms) |
|---|---|---|
| 0.25 (full ceiling) | 252 | 504 |
| 0.20 | 393 | 786 |
| 0.15 | 698 | 1,396 |
| 0.125 (half ceiling) | 1,005 | 2,010 |

`scripts/nudge_pilot_power.py` reproduces this table and the stage-2
re-power rule.

**Stage 1 (online panel, n = 50/arm, N = 250, EN+JP).** Deliverable: an
**effect-size prior for the primary contrast**, not merely instrument
validation — report d̂ with its standard error, endpoint SDs, the
within-participant task correlation (for mixed-model gain), and construct
reliability. Stage 1 is powered only for d ≥ 0.56 and is explicitly
non-confirmatory.

**Stage 2 (confirmatory).** Re-power on stage-1 evidence with the
pre-specified rule: plan against d_plan = max(0.10, d̂ − SE(d̂)) — the lower
68% bound, floored — with the mixed model over two tasks credited only at the
stage-1-estimated task correlation.

**Feasibility flag (raised now, not after stage 1).** If d_plan lands near
the half-ceiling case, the primary contrast alone needs ~2,010 completes.
For scale: FTAS — an established, interviewer-run, multi-facility intercept
operation — captured ~289 rail respondents/month prefecture-wide and ~120/month
in the three corridor municipalities post-opening. A passive QR intercept at
three stations will yield well below that; even at FTAS-scale corridor
capture, 2,010 completes ≈ 17 months of fielding. **An intercept-only stage 2
is not credible below d ≈ 0.21** (six months at corridor-scale capture ≈
360/arm). Pre-specified mitigations, in preference order:

1. **Hybrid recruitment:** power the main sample from an online panel screened
   for planned/recent Hokuriku rail travel; nest the station QR intercept as
   an external-validity subsample (target n ≈ 300–500), analyzed for
   direction-consistency, not powered alone.
2. **Arm reduction:** stage 2 drops to `control` / `transport_access` /
   `combined`, concentrating recruitment on the primary contrast.
3. **Window extension** only if (1) is unavailable.

## Analysis plan

Primary: mixed model, visit-intention ~ condition + strata + task, participant
random intercept; primary contrast tested two-sided at α = 0.05. Mediation:
condition → perceived friction → visit intention (bootstrap CI on the
indirect path), mirroring SEM Stage 2. Secondary contrasts
Holm-corrected. Manipulation check: accuracy item by arm. No interim
efficacy analysis in stage 1; stage 1 estimates flow only into the stage-2
power rule.

## Known limitations

- Intention, not behavior: the endpoint is planning commitment in a
  hypothetical task, an upper bound on field conversion.
- Selection ceiling logic assumes the car–rail satisfaction gap is
  friction-attributable at most; if it is mostly mode self-selection, even
  d = 0.125 is optimistic.
- Static-mode fallback assignment is not block-balanced; confirmatory claims
  require the server-side path.
- Stimulus facts are instrument copy, not travel advice; verify before
  fielding.
