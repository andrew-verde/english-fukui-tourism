# Data

Raw and large intermediate data are **not committed** to this repo. They are
reconstructed from pinned sources. After cloning:

    make fetch

This repopulates `output/` from sources pinned in
`config/official_fukui_sources.yaml` and `config/national_data_sources.yaml`.

A full backup of pulled data also lives in Google Drive as a convenience. Fetch
scripts remain source of truth.

This project is early WIP. Byte-level SHA verification of fetched files is not
yet enforced; re-fetches may differ when upstream data changes.
