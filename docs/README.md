# Documentation Index

Thesis: tourism friction in Fukui Prefecture around the 2024 Hokuriku
Shinkansen extension. Primary analyses are the Shinkansen
difference-in-differences and the FTAS two-stage SEM (ADR 0001); the
English-language Google review layer is exploratory supporting evidence.

Start here, in order:

- [`results_overview.md`](results_overview.md) — one-page map of the
  quantitative arc (impact → mechanism → intervention) with headline numbers
  and the make target that regenerates each.
- [`source_ledger.md`](source_ledger.md) — every reported number traced to
  command, script, input, and artifact, with verified / simulated-demo /
  estimated / hypothesis status labels.
- [`reproducibility_checklist.md`](reproducibility_checklist.md) —
  journal-review-oriented setup, dependency, code-availability, and
  no-network reproduction checklist.
- [`methods_appendix.md`](methods_appendix.md) — per-analysis statistical
  traceability: research question → test choice → assumptions →
  configuration → caveats. §I covers provenance guards and AI-assistance
  disclosure.
- [`adr/`](adr/) — design decisions: 0001 (FTAS SEM + Shinkansen DiD as
  primary contribution), 0002 (retire the Likert pilot path).
- [`national_data_integration_plan.md`](national_data_integration_plan.md) —
  national supplementary data (JTA 宿泊旅行統計調査 accommodation panel as
  behavioral DiD outcome, JR West ridership as first-stage evidence): what was
  evaluated, what was dropped, pipeline status, and remaining steps.

Generated summaries (rebuild via Makefile, do not hand-edit):

- `../output/hokuriku_merged/did_event_study_report.md` — DiD event study and
  robustness battery (`make hokuriku-did-event-study`).
- `../output/sem/` — SEM stage 1/2 results and nudge priority ranking
  (`make sem-ftas`, `make nudge-ranking`).
- `../output/official_fukui/statistical_summary_official.md` — FTAS
  official-data summary (`make synth-official`).
- `../output/statistical_summary.md` — exploratory English-review results
  (`make synth`).
- `../output/data_manifest.md` — row counts, schemas, hashes for key datasets
  (`make data-manifest`).

Historical:

- [`code4fukui_data_integration_plan.md`](code4fukui_data_integration_plan.md)
  — superseded 2026-06; kept as a record of the May 2026 planning state. See
  its status header for what was executed, superseded, or dropped.

Canonical terminology lives in `../CONTEXT.md`; setup and pipeline order in
the top-level `../README.md`.
