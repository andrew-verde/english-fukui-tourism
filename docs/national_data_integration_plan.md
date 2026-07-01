# National Supplementary Data Integration Plan (JNTO / JTA / MLIT / JR)

Research date: 2026-06-12. Scope: what national public data can supplement the
FTAS SEM + Shinkansen DiD analyses, and how to obtain JR ridership data.

## What was found

### Tier 1 — directly usable, monthly, prefecture-level

| Source | Data | Granularity | Access | Pipeline |
|---|---|---|---|---|
| JTA 宿泊旅行統計調査 (e-Stat code 00601020) | Overnight stays: total / Japanese / foreign; occupancy | Monthly, prefecture, since 2007 | e-Stat API (free AppID) | `make fetch-estat` |
| JNTO statistics site (statistics.jnto.go.jp) | Visitor arrivals, prefecture overnight stays | Monthly, prefecture | Tableau views; CSV download per view, no API | manual cross-check |
| JR West press releases | Hokuriku Shinkansen (Kanazawa–Tsuruga) boardings, first 12 months; FY2024 transport density | Line/section level | Free PDFs | `make fetch-national-direct` |
| FF-DATA 訪日外国人流動データ (e-Stat code 00600466) | Cross-prefecture foreign visitor flow: nationality × purpose × transport mode, inter-prefecture OD | Quarterly/annual, prefecture, since 2014 | 国土交通データプラットフォーム API (mlit-data.jp, free AppID reg, XML/JSON/CSV, ≤100 items/query) or e-Stat file download | new — see below |

### Tier 2 — context / robustness

| Source | Data | Limitation |
|---|---|---|
| JTA 訪日外国人消費動向調査 (00601030) | Inbound spending + prefecture visitation by nationality | Quarterly only |
| MLIT 鉄道輸送統計調査 (00600350) | Rail passengers/revenue, monthly | Operator-level only — JR West aggregate, no line split |
| 国土数値情報 S12 | Station-level annual boardings (GeoJSON) | FY2022 latest; post-opening release ~2027. Pre-extension baseline only |
| Fukui Pref. 観光客入込数 | Site/municipality visitor counts | Annual, PDF only |
| RAIDA (raida.go.jp) | RESAS successor — prefecture travel dashboards | No API (re-verified 2026-07-01); RESAS API discontinued March 2025, do not cite it. Dashboard covers lodging-guest-attribute change + regional economic effect for Fukui; usable only as manual descriptive/qualitative citation, never as pipeline input. Site notes some features discontinued as of March 2026 — re-check before citing |

### Thesis fit

- **New DiD outcome variable**: monthly prefecture overnight stays (00601020),
  Fukui (18000) vs Ishikawa/Toyama/Gifu controls, around 2024-03-16. This is a
  *hard count* outcome complementing the survey-based NPS/satisfaction DiD —
  answers the "did behavior change, not just sentiment" critique.
- **First-stage / mechanism evidence**: JR West press-release ridership shows
  the treatment actually delivered passenger volume; cite as descriptive
  first-stage, not as an estimated quantity.
- **Triangulation**: JNTO prefecture overnight stays as cross-check on the JTA
  series (same underlying survey, different publication path).
- **FF-DATA flow panel (new, found 2026-07-01)**: combines JTA 訪日外国人消費動向調査
  + civil aviation bureau + immigration stats into cross-prefecture foreign
  visitor flow (nationality × purpose × transport mode), quarterly/annual.
  Complements the accommodation panel by answering "did visitors actually move
  into Fukui" rather than just "did stays rise" — a second hard-count outcome
  for the event study, built from independent source surveys (less mechanical
  overlap with 00601020 than another stays series would be). Access via
  mlit-data.jp API (separate AppID registration from e-stat) or e-Stat file
  download (00600466). Granularity is coarser (quarterly, not monthly) so
  treat as a robustness/triangulation series alongside the monthly
  accommodation panel, not a replacement.

Caveats for the methods appendix: 宿泊旅行統計調査 has a facility-size
reporting threshold and preliminary→confirmed revisions (use confirmed or 2nd
preliminary values only, flag vintage in the manifest); the DiD identification
discussion must address the Noto earthquake (2024-01-01) hitting Ishikawa —
already a concern for the survey DiD, equally binding here.

## JR data: what is and is not gettable

- **Public now**: line-level Hokuriku ridership via press releases (fetched by
  this pipeline); JR West monthly usage PDFs (westjr.co.jp/company/ir/finance/monthly/);
  operator-level MLIT stats.
- **Not public**: station-level post-opening boardings (Tsuruga/Fukui/Awara-Onsen).
  国土数値情報 S12 won't carry FY2024 until ~2027.
- **JR East Suica data products (駅カルテ)**: wrong operator — JR East only, no
  Hokuriku coverage. Dead end.
- **Formal request route**: JR West has no published academic-data program.
  Realistic path: formal letter via https://www.westjr.co.jp/global/en/support/inquiry/
  with advisor letter, institutional affiliation, exact ask (monthly boardings
  at Tsuruga/Fukui/Awara-Onsen, 2024-03 onward), and stated public-benefit
  purpose. Expect weeks and possible refusal — treat as upside, not plan-of-record.
- **Mobility proxies**: Agoop / NTT docomo Mobile Spatial Statistics have
  academic-collaboration precedent (docomo + NILIM + Univ. of Tokyo) but
  require B2B negotiation — out of scope for solo timeline unless advisor has
  an existing channel.

## Implementation structure (built)

```
config/national_data_sources.yaml          # estat: (API, audit only) + direct: (file) sources
scripts/fetch_estat_data.py                # e-Stat API discovery/pull — see dead-end note below
scripts/fetch_national_direct.py           # JTA Excels + JR West PDFs, sha256 manifest
scripts/build_accommodation_panel.py       # Excel → tidy prefecture × month panel + summary
output/national_stats/raw/                 # fetched files (gitignored like other output)
output/national_stats/accommodation_panel.csv
```

Make targets: `fetch-national-direct`, `accommodation-panel`,
`fetch-estat-list`/`fetch-estat` (audit only).

### e-Stat API dead-end (verified 2026-06-12)

The 00601020 API DB tables are frozen at 2014–2016 (32 tables, all time axes
end 2016; publication moved to Excel in 2019). Current data is the annual
Excel releases on the MLIT page, which `fetch_national_direct.py` pulls:
2018–2024 confirmed values + 2025 annual preliminary + 推移表. The panel
builder parses 第2表 (total stays) and 参考第1表 (foreign stays, facilities
with 10+ employees only — not level-comparable to total) per month.

Panel status: built and gated (4,512 rows = 8 years × 47 prefectures × 12
months, zero nulls; vintage column flags 2025 as preliminary). 2018–2019 give
a pre-COVID parallel-trends window; 2020–2021 cover the COVID regime and
should enter the event study as pre-period but be flagged in the
parallel-trends discussion. Fukui March total stays: 322,200 (2018) →
200,890 (2022) → 340,140 (2024, opening on the 16th).

### Remaining steps (ordered)

0. Build FF-DATA flow panel: `scripts/fetch_ff_data.py` (mlit-data.jp API,
   AppID env var, prefecture × quarter, nationality/purpose/transport
   dimensions) → `scripts/build_ff_data_panel.py` (tidy panel, mirrors
   `build_accommodation_panel.py`) → `output/national_stats/ff_data_panel.csv`.
   Add `ff_data` block to `config/national_data_sources.yaml`. Gate with a
   test mirroring `tests/test_accommodation_panel.py`. No source-ledger row
   until a number from this panel is actually cited.
1. Extend `hokuriku_did_event_study.py` (or a sibling script) to run the same
   event-study spec on `output/national_stats/accommodation_panel.csv`
   (log stays, prefecture × month, treatment = Fukui, opening 2024-03-16;
   decide handling of the half-treated March 2024 cell).
2. Extract first-year ridership figures from the JR West PDF into the source
   ledger as a descriptive first-stage row.
3. **Standing reminder — 2025 confirmed values.** The 2025 rows are annual
   preliminary (年間の速報値, fetched 2026-06-12). JTA publishes confirmed
   values (年の確定値) around mid-year; the 2024 confirmed file appeared by
   June 2025, so expect the 2025 file mid-to-late 2026. When it appears on
   https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html:
   replace the `jta_accommodation_2025_preliminary` entry in
   `config/national_data_sources.yaml` with the confirmed-file URL, update
   `SOURCES` in `scripts/build_accommodation_panel.py`, then re-run
   `make fetch-national-direct` + `make accommodation-panel`. The builder
   logs a warning on every run until no preliminary vintage remains, and the
   source-ledger row must flip from preliminary in the same commit
   (ledger rule 2). Any 2025 number cited before then must say "preliminary".
4. Optional: draft the JR West formal data-request letter with advisor.

Source-ledger rule applies: no number from these sources appears in any
document until it has a verified row in `docs/source_ledger.md`.

## Licensing

e-Stat and MLIT data: government statistics, attribution required (survey name
+ ministry + access date). JNTO: cite "Japan Tourism Statistics (JNTO)". JR
West press releases: cite as corporate disclosures. All compatible with
academic use.
