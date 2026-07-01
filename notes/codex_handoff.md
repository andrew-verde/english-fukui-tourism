# Codex Handoff — new open-data arms for english-fukui-tourism

Source copy: `/home/andrewgreen/.codex/attachments/70479f01-604c-430f-a71e-a2142c3aac96/codex_handoff.md`

This repository-local handoff tracks implementation of three open-data arms:

1. Locality reservation DiD/event study using Fukui Station and Obama as treated
   panels, with Echizen Coast and Mikata-goko retained as post-only context.
2. Resident-revitalization descriptive series from `fukui-vision-data`.
3. Municipal synthetic control from `japan-kanko-stat`.

Event date: `2024-03-16`.

## Required reservation sources

| key | repo | commit | sha256 | rows | role |
|---|---|---|---|---:|---|
| `fukui_station_reservation` | `code4fukui/fukui-station-kanko-reservation` | `2e6d8e6a30b3518d4d2c36440555a1de8aaaed69` | `a865c9b769b3517de723b24200f3bb3139a2c952dbb258e926e48091120e3aa5` | 1095 | treated |
| `obama_reservation` | `code4fukui/obama-kanko-reservation` | `732082687a3cdfad5c403331c78c830265772afd` | `d04aa6c9d08cc3e940da10b65fd4e8d6a7c88e327936945ab8e4463ead055b73` | 1071 | treated |
| `echizen_coast_reservation` | `code4fukui/echizen-coast-kanko-reservation` | `6742d707dbfc3247893c3e8ce174f250e3820a15` | `0e4c9a857c47679dda102823d6e98d7de8b6f3489657b59d6ae982b284d55d22` | 698 | post-only |
| `mikatagoko_reservation` | `code4fukui/mikatagoko-kanko-reservation` | `0e715aa3f6d2a5a467ad0aca071d4c1619448a5b` | `53be386fa5a39a8cf0ada7f3c1818923c445daf28e352dd9976af8cc1a8e43a5` | 523 | post-only |

Parse reservation CSVs by column name. Mikata-goko orders columns differently.
Expected set: `date_visit,n_stay,n_people,n_room,amount_fee,n_reserve`.

Vision pins:

- overview: commit `7eba2ff6ba50f73bb28e36554787882231007527`,
  SHA256 `9bba3649b4558e1a44b81afe8cd110f4d077d566bac43258c22b31506508b68e`,
  7 rows.
- timeseries: same commit, SHA256
  `47c9cc79a32b26307b4437600861961c279b62e81b60c5fd739e3d0101abb930`,
  159 rows.

Vision data is aggregate, descriptive evidence—not microdata, SEM, ITS, or causal
evidence. Note postal-to-web survey mode shift.

National synthetic control uses `code4fukui/japan-kanko-stat` commit
`dfb906975b63adcaef20a3e7a35f2a10ab22ada5`, files
`data/city2021.csv` through `data/city2025.csv`. Facts later supplied:

| file | sha256 | rows |
|---|---|---:|
| `city2021.csv` | `20db2aaaa766c1985ee09b37f741f27e40902fe320ce7649078deea1259fe554` | 22408 |
| `city2022.csv` | `e47e44560bcc08537306bf9a99c637409fffefb91863eeb077000bedc23aabb4` | 22400 |
| `city2023.csv` | `9a6a15f5f431d26b3116033a8b8cd224bbe9757936f2a1ff294f19b01ef3faf6` | 22412 |
| `city2024.csv` | `3349691e0613829f3ec267eac2f38bd5415d5a4c61f1ddae114f81f185619953` | 22413 |
| `city2025.csv` | `7c31fed0a71168b684e61ecc5e092cf8d63679494a9eeeac384ceb58f17d5216` | 22434 |

Primary synthetic-control unit: Fukui City `18201`; outcome `人数`, log scale;
event month `202403`; pre-fit `202101–202402`; exclude prefectures 15–18 from
primary donor pool. Report gap + placebo inference, plus Ishikawa-included
robustness. Mobile-derived levels are estimated, not census headcounts.

Required ADRs:

- `0003-locality-reservation-did-arm.md`
- `0004-resident-revitalization-descriptive-arm.md`
- `0005-national-synthetic-control-arm.md`

Original handoff test oracles:

| locality | min | max | days | pre | post | pre people | post people | pre fee | post fee |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Fukui Station | 2023-10-01 | 2026-09-29 | 1095 | 167 | 928 | 238.102 | 464.261 | 1725634.2 | 3686341.5 |
| Obama | 2023-10-25 | 2026-09-29 | 1071 | 143 | 928 | 55.986 | 132.128 | 883804.9 | 2014277.6 |
| Echizen Coast | 2024-11-01 | 2026-09-29 | 698 | 0 | 698 | — | 67.441 | — | 2243630.6 |
| Mikata-goko | 2025-04-24 | 2026-09-28 | 523 | 0 | 523 | — | 127.927 | — | 2028429.8 |

National oracle: 60 months; 38 pre months; 17 Fukui municipalities; 1,806
eligible donors before completeness filtering; 1,709 full-coverage donors.
Fukui City pre/post means: 75,166.9 / 113,439.0.

Implementation order: pinned sources → checksum fetch → loader/oracle tests →
reservation estimator → vision descriptive figure/table → national panel and
synthetic control → ledger + ADRs.
