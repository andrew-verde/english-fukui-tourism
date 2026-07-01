# ADR 0003: Locality reservation panels as a second DiD arm

Date: 2026-07-01
Status: accepted (extends ADR 0001)

## Context

ADR 0001 established the Shinkansen DiD/event-study on survey outcomes plus JTA
guest-nights as the causal layer. That design measures friction *impact* through
survey-reported outcomes but has no high-frequency behavioral outcome and no
economic (revenue) measure.

Code4Fukui publishes daily accommodation-reservation panels per tourism locality,
sharing the column set of the already-ingested `fukui-kanko-reservation` feed
(`date_visit, n_stay, n_people, n_room, amount_fee, n_reserve`). Four localities
were evaluated against the March 2024 (2024-03-16) Shinkansen extension:

- `fukui-station-kanko-reservation` — 2023-10-01→2026-09-29, 167 pre-event days
- `obama-kanko-reservation` — 2023-10-25→2026-09-29, 143 pre-event days
- `echizen-coast-kanko-reservation` — 2024-11-01→ (no pre-period)
- `mikatagoko-kanko-reservation` — 2025-04-24→ (no pre-period)

`mikatagoko` orders its columns differently (`n_reserve`/`n_people` swapped), so
loading is by column name, not position.

## Decision

1. **Add a locality-panel DiD as a second, behavioral arm** alongside the survey
   DiD. Treated: Fukui-station and Obama (the two localities with a pre-period).
   Control: existing Ishikawa reservation localities, cross-checked against the
   national synthetic control (ADR 0005).
2. **Add `amount_fee` (revenue) as a new outcome**, log-transformed, alongside
   `n_people`. This is the project's first economic-impact measure.
3. **Post-only localities (echizen-coast, mikatagoko) are excluded from the DiD**
   and used only for descriptive spatial-spillover context. They are never
   plotted as DiD peers.
4. **Sources are commit-pinned with sha256 gates**, matching the existing
   provenance pipeline; the `latest_rsv_sum.csv` files update daily, so the
   immutable commit is the anchor and the checksum verifies the fetched bytes.

## Consequences

- Adds a high-frequency (daily) behavioral outcome and a revenue outcome the
  survey arm cannot provide.
- **The pre-window is a single winter (2023-10 → 2024-03-15).** Parallel-trends
  can be shown but not validated across a full seasonal cycle; the DiD is
  reported with this as an explicit limitation and, where feasible, a
  seasonally-adjusted specification.
- Only two localities carry the DiD; results are locality-specific, not a
  prefecture-wide reservation effect.
- Reservation panels are booking-system records for participating properties,
  not a census of all accommodation — coverage is a convenience sample.

## Alternatives considered

- **Include all four localities in the DiD:** rejected — two have no pre-period
  and would contribute only post-event levels, biasing a naive estimator.
- **Position-based CSV parsing shared across localities:** rejected — mikatagoko's
  column order differs; name-keyed loading with a post-load column-set assertion
  is required.
- **Treat reservations as the primary causal arm:** rejected — the single-winter
  pre-window is too thin; the national synthetic control (ADR 0005) is the
  stronger causal design, with reservations as behavioral corroboration.
