# Reproducibility Checklist

## Environment

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python -m pytest tests/ -v
```

## No-network reviewer path

```bash
make reproduce-submission
```

This rebuilds maintained official-data outputs, SEM, nudge ranking, DiD/event
study, and aggregate manifest from pinned inputs.

## Reviewer checks

- Confirm Git LFS inputs materialized.
- Compare source-manifest hashes and vintages.
- Verify respondent deduplication audits.
- Verify friction denominators use eligible official-survey rows.
- Inspect SEM fit indices and staged model outputs.
- Inspect DiD pre-trends, event-study coefficients, and robustness estimates.
- Confirm generated outputs contain no platform-review datasets.
- Confirm `output/data_manifest.json` covers official, SEM, DiD, national, and
  standalone Chinese side-analysis tables only.

Network fetch targets are excluded from no-network reproduction.
