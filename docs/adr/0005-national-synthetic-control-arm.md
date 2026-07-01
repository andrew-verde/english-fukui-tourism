# ADR 0005: National synthetic control as the primary causal counterfactual

Date: 2026-07-01
Status: accepted (extends ADR 0001, amends the control strategy)

## Context

ADR 0001's DiD uses Ishikawa and Toyama as controls for Fukui. That control is
compromised: the **2024-01-01 Noto Peninsula earthquake** struck Ishikawa two
months before the March 2024 Shinkansen extension, contaminating it with a
large, simultaneous, opposite-signed tourism shock. A cleaner counterfactual was
needed for the headline causal estimate.

`code4fukui/japan-kanko-stat` provides **monthly municipal tourist-visitor counts
(観光来訪者数)** for all 47 prefectures, **2021-01 → 2025-12 (60 months, 38
pre-event)**, at 市区町村 grain. All 17 Fukui municipalities are present with full
coverage. Excluding the four Hokuriku-line-affected prefectures (15 Niigata,
16 Toyama, 17 Ishikawa, 18 Fukui) leaves **1,709 municipalities with full
60-month coverage** as a donor pool. Raw pre/post means already show a large
post-event lift (Fukui City +51%; Katsuyama +79%; Eiheiji +76%), but that
conflates the extension with the nationwide post-COVID recovery.

## Decision

1. **Adopt a synthetic-control design as the primary causal counterfactual**,
   with the Ishikawa/Toyama DiD retained as a secondary comparison.
2. **Treated unit:** 福井市 (area_code 18201) as primary; the design is repeated
   per Fukui municipality for heterogeneity.
3. **Donor pool excludes prefecture codes 15–18** (the Hokuriku-affected set);
   municipalities with any coverage gap are dropped before fitting.
4. **Method:** Abadie synthetic control — convex donor weights minimizing
   pre-period (202101–202402) RMSPE — reporting the treated-minus-synthetic gap
   plot and placebo/permutation inference across donors. Outcome `人数` is
   log-transformed.
5. **Robustness:** re-run with Ishikawa included as a donor to show the estimate
   is not an artifact of its exclusion; report both.
6. **Provenance:** the five per-year `cityYYYY.csv` files are commit-pinned with
   sha256 gates (not `all.csv`, which covers only 2021–22).

## Consequences

- Provides a counterfactual free of the Noto-earthquake contamination and with a
  38-month pre-window — substantially stronger than the single-winter reservation
  pre-period (ADR 0003).
- Doubles as a within-prefecture heterogeneity panel across the 17 Fukui
  municipalities.
- `人数` is a mobile-location-derived vendor estimate, not a census; levels are
  model-based, so the arm supports **relative/gap** inference and is ledgered as
  `status: estimated`, not absolute headcounts.
- Adds a synthetic-control implementation and its placebo-inference machinery to
  the codebase.

## Alternatives considered

- **Ishikawa/Toyama DiD as the sole causal design:** rejected as primary — Noto
  earthquake contamination; retained as a secondary check.
- **`all.csv` as the data source:** rejected — covers only 2021–2022; the per-year
  city files give the full 2021–2025 panel.
- **Including Hokuriku prefectures in the donor pool:** rejected for the main
  specification (they share the treatment/shock); used only in the robustness run.
