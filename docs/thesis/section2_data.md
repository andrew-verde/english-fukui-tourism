# 2. Data, Provenance, and Reproducibility

## 2.0 Purpose

This thesis's empirical claims rest on public open data, none of it collected
by the author — which makes provenance discipline, not data collection, the
methodological contribution of this chapter. The governing rule is simple and
enforced by machinery rather than intention: **every number printed in an
outward-facing document must be traceable to a committed artifact that a named
`make` target regenerates from pinned inputs.** This chapter describes the data
families, the pinning and checksum discipline that fixes them, the units and
measurement conventions built on top of them, and the single-command
reproduction contract offered to a reviewer.

## 2.1 Data families

**Survey microdata (Chapters 3–4, 6).** The core source is the Fukui Tourism
Attitude Survey (FTAS), distributed as open data and pinned at its 2026-06-30
upstream vintage: 97,866 response rows, which the documented ID/time
deduplication rule reduces to **51,399 unique respondents** (46,467 repeat
responses dropped — the ~47% repeat share that also motivates Chapter 3's
clustering). Among deduplicated respondents, 15.4% (7,908 of 51,399) report
experiencing inconvenience — the selection-bias-free exposure underlying the
SEM. For the cross-prefecture design of Chapter 3, the Hokuriku consortium's
merged file adds the Ishikawa QR survey (and, from 2025 only, Toyama):
103,807 identically-worded responses from April 2023 to June 2026. The full
license chain is CC-BY (merged file CC-BY 4.0; FTAS CC-BY 4.0; Ishikawa
CC-BY 2.1 JP), recorded with per-file SHA-256 hashes in
`output/hokuriku_merged/source_manifest.json`.

**Municipal visitor-count panel (Chapter 5).** The synthetic-control arm reads
`code4fukui/japan-kanko-stat`: monthly municipal tourist-visitor counts for
all 47 prefectures, 2021–2025, pinned to upstream commit `dfb9069` with
per-file SHA-256 gates on the five annual city files. The counts are
mobile-location-derived vendor estimates, so the panel is ledgered as
`estimated` and supports gap and relative inference only — a restriction
Chapter 5 inherits explicitly.

**Supporting official series.** A JTA accommodation panel, four
checksum-gated locality reservation panels, and the Fukui Vision resident
survey are staged as descriptive companions; each is ledgered with the status
that bars it from carrying causal claims. A Chinese social-media layer exists
in the repository as a quarantined side project and is never cited as thesis
evidence.

## 2.2 Provenance discipline

Three layers fix the inputs. First, **a lock file**:
`config/official_fukui_sources.yaml` records, for every Code4Fukui input, the
upstream repository, the full Git commit, the path at that commit, and the
expected SHA-256; the fetcher (`scripts/fetch_code4fukui_data.py`) downloads
from immutable commit-addressed URLs only — a mutable branch or GitHub Pages
URL is never a thesis input — and verifies content before replacing anything.
Second, **manifests**: each output family carries a source manifest with
upstream URLs, vintages, and hashes, and `make data-manifest` aggregates row
counts, schemas, and SHA-256 values for the maintained analytical datasets
into `output/data_manifest.json`. Third, **a source ledger**
(`docs/source_ledger.md`): one row per headline number, with a controlled
status vocabulary — `verified`, `estimated`, `simulated/demo`, `hypothesis` —
and the rule that no number appears in an outward-facing document without a
row. Raw thesis-critical microdata is tracked in Git LFS so a fresh clone
materializes the exact bytes analyzed.

Two provenance gates are load-bearing enough to name. The causal arm's
per-municipality summary (Feed A, `data/causal/fukui_municipalities_scm.csv`)
is pinned by exact SHA-256
(`ff6cd1af…`) and guarded by checksum tests in two test modules; every
downstream synthesis number trusts that byte-identity. And a provenance guard
in the test suite (`tests/test_report_provenance.py`) scans every document
under `docs/` for statistical claims and fails the build if the document cites
no reproduction path — the discipline of this chapter is itself enforced by
`make test`.

## 2.3 Units and measurement

The unit of survey analysis is the *deduplicated respondent*; text-tag rates
use eligible free-text respondents as the denominator, and
structured-response rates use their documented eligible populations
(`docs/methods_appendix.md`). Friction coding is reproducible multi-label
keyword tagging against a versioned Japanese codebook
(`config/official_japanese_friction_codebook.yaml`, implemented in
`src/friction/`); tags are measured indicators with documented codebook
limitations, not ground truth. Municipalities are identified by JIS area
codes throughout, and 市町村 in FTAS records the *response location*, not
residence — a limitation Chapters 4 and 6 carry forward.

## 2.4 The reproduction contract

A reviewer reproduces the thesis with one command:

```bash
make reproduce-submission
```

This runs the full test suite (131 passed, 1 skipped at this writing) and
rebuilds, in dependency order, the causal arm and its robustness battery, the
FTAS builds and official statistics, the SEM and nudge ranking, the synthesis
join and durability mechanisms, the DiD event study, all thesis figures, and
the aggregate manifest. The chain is **offline except one target**:
`synth-causal-arm` fetches the pinned code4fukui panel over the network to
regenerate the byte-stable Feed A fixture (ADR 0007 records why this is
documented rather than vendored away). All other targets read pre-staged
local inputs; the one git-untracked prerequisite,
`output/national_stats/japan_kanko_stat_panel.csv`, is staged via
`make fetch-japan-kanko-stat japan-kanko-panel`.

Two standing rules complete the contract. Any change upstream of a printed
number re-runs the *full* chain, not just the touched target — synthetic-
control inputs drift downstream silently otherwise. And refreshed upstream
fetches never overwrite pinned vintages without a reviewed diff of manifests
and estimates; updating a vintage is a deliberate, ADR-logged event. For
publication, the replication package is to be deposited in a durable
repository (Zenodo, OSF, or institutional) under a DOI, citing the original
data creators and exact archived versions — a GitHub repository is a mirror,
not an archival identifier.
