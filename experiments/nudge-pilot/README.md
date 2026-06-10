# Fukui Nudge Pilot Experiment

This is a standalone browser-based pilot instrument for testing whether tourism-planning nudges change:

- information clarity
- perceived friction
- planning confidence
- visit intention
- trust in planning information

The app is intentionally dependency-free. It can run as a static site during pilot testing and can later be moved into a separate repository or connected to a real survey/data-collection backend.

## Run Locally

From the repository root:

```bash
python3 -m http.server 8765 --directory experiments/nudge-pilot
```

Open:

```text
http://localhost:8765
```

Do not open `index.html` directly from Finder for testing. Browser security rules can block loading `study-config.json` from a local file URL.

## Study Design

The pilot uses a between-subjects assignment. Each participant is assigned to one condition:

- `control`
- `transport_access`
- `opening_hours_availability`
- `itinerary_fit_time_cost`
- `combined`

Each participant completes the same two tourism-planning tasks, then answers the same SEM-oriented Likert items after each task. The current tasks use:

- Eiheiji Temple
- Fukui Prefectural Dinosaur Museum

The current app stores no names, emails, precise locations, or reviewer identity data.

## Data Export

Responses are saved in browser local storage. At the end of a session, use:

- **Download JSON** for the full record, including task events.
- **Download CSV** for flattened pilot analysis.

For a supervised pilot, export after each participant or at the end of each testing session. For remote deployment, replace local storage with a backend, Qualtrics, Google Forms, REDCap, Supabase, or another approved data store.

## SEM Data Shape

The exported CSV is one row per participant/session. Important column groups:

- `assigned_condition`
- `background_*`
- `task_*`
- `survey_*_information_clarity_*`
- `survey_*_perceived_friction_*`
- `survey_*_planning_confidence_*`
- `survey_*_visit_intention_*`
- `survey_*_information_trust_*`

For SEM, keep the item-level columns. Do not collapse to means until after checking reliability and the measurement model.

## Pilot Checklist

Before using this with real participants:

1. Confirm consent and ethics-review requirements with the lab or university.
2. Run 5-10 internal dry runs to catch confusing wording.
3. Check that exported CSV columns import cleanly into R, Python, jamovi, or SPSS.
4. Revise task text if participants miss the planning scenario.
5. Run a 20-30 participant pilot before a larger SEM sample.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Static app shell |
| `styles.css` | App styling |
| `app.js` | Random assignment, study flow, local storage, exports |
| `study-config.json` | Conditions, tasks, construct items, background questions |

## Integration Notes

This project should stay separate from the observational friction-analysis pipeline until the pilot design stabilizes. A later integration can map:

- observed friction codes -> candidate nudge condition
- nudge condition -> experimental exposure
- post-task survey items -> SEM latent constructs
- task success/time/accuracy -> behavioral outcome checks
