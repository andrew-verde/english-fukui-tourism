# Fukui Nudge Pilot Experiment

This is a standalone browser-based pilot instrument for testing whether tourism-planning nudges change:

- information clarity
- perceived friction
- planning confidence
- visit intention
- trust in planning information

The app is intentionally dependency-free. It can run as a static site during pilot testing, or as a Vercel app with serverless API routes that write completed responses to Supabase.

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

This static local mode saves responses only to browser local storage. Database submission is enabled when the app is deployed on Vercel with the Supabase environment variables below.

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

## Remote Data Collection

Recommended production-style stack:

```text
Vercel static app + Vercel serverless API routes + Supabase Postgres
```

The browser never receives the Supabase service-role key. Completed sessions are sent to `/api/submit`, and that Vercel function writes to Supabase from the server side.

### 1. Create Supabase Table

In Supabase:

1. Open your project.
2. Go to **SQL Editor**.
3. Paste and run:

```text
experiments/nudge-pilot/database/supabase-schema.sql
```

This creates:

- `public.nudge_pilot_responses`
- indexes for study, condition, and completion date
- row-level security enabled
- deny-by-default anonymous policies
- `public.nudge_pilot_sem_export` view

### 2. Add Vercel Environment Variables

In Vercel:

1. Open the project.
2. Go to **Settings -> Environment Variables**.
3. Add:

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_TABLE=nudge_pilot_responses
ALLOWED_ORIGINS=https://your-vercel-project.vercel.app
```

`SUPABASE_TABLE` is optional if you keep the default table name. `ALLOWED_ORIGINS` is also optional for normal same-origin Vercel deployment; set it if you later post from another approved domain.

Use the **service role key** only in Vercel environment variables. Do not paste it into `app.js`, `study-config.json`, or any browser-visible file.

### 3. Deploy on Vercel

Import this GitHub repository into Vercel and use:

```text
Framework Preset: Other
Root Directory: experiments/nudge-pilot
Build Command: empty
Output Directory: empty or .
Install Command: empty
```

After deployment, visit:

```text
https://your-vercel-project.vercel.app/api/health
```

Expected configured response:

```json
{
  "status": "ok",
  "storage_configured": true,
  "study": "fukui_nudge_pilot"
}
```

If `storage_configured` is `false`, Vercel does not have the Supabase environment variables yet.

### 4. Test One Fake Participant

Complete a fake session on the deployed Vercel URL. The final screen should show:

```text
Database status: Saved to Supabase (...)
```

Then check Supabase:

```sql
select
  session_id,
  assigned_condition,
  completed_at,
  flattened
from public.nudge_pilot_responses
order by completed_at desc
limit 5;
```

## Local Export

Responses are always saved in browser local storage as a backup. At the end of a session, use:

- **Download JSON** for the full record, including task events.
- **Download CSV** for flattened pilot analysis.

For supervised pilots, export after each participant or at the end of each testing session even when Supabase is enabled. This gives you a backup if a network request fails.

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

Supabase stores both:

- structured JSON columns: `background`, `tasks`, `surveys`, `final_responses`, `events`
- a `flattened` JSON column with spreadsheet-style keys

This keeps the raw response intact while still making SEM export straightforward.

## Security Defaults

- The app does not ask for names, emails, phone numbers, or precise location.
- The browser submits only to same-origin `/api/submit`.
- The API rejects browser requests from unexpected origins unless they are listed in `ALLOWED_ORIGINS`.
- Supabase credentials are kept in Vercel serverless environment variables.
- Row-level security is enabled on the Supabase table.
- Anonymous Supabase reads and writes are denied.
- The API validates required fields before database insertion.
- Request bodies are capped at 250 KB.
- `session_id` is unique, so retries update the same response instead of creating duplicates.
- IP addresses are not stored by the API. User agent is stored for basic debugging and can be removed from the schema/API if your ethics review prefers less metadata.

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
| `app.js` | Random assignment, study flow, local storage, remote submission, exports |
| `study-config.json` | Conditions, tasks, construct items, background questions |
| `api/health.js` | Vercel health/configuration check |
| `api/submit.js` | Vercel -> Supabase response insertion |
| `database/supabase-schema.sql` | Supabase table, indexes, RLS policies, export view |
| `.env.example` | Environment variable template |
| `vercel.json` | Basic Vercel headers and clean URLs |

## Integration Notes

This project should stay separate from the observational friction-analysis pipeline until the pilot design stabilizes. A later integration can map:

- observed friction codes -> candidate nudge condition
- nudge condition -> experimental exposure
- post-task survey items -> SEM latent constructs
- task success/time/accuracy -> behavioral outcome checks
