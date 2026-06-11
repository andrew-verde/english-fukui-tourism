# FTAS SEM — Stage 2 (friction reporters, n=2,503)

Sample: respondents with reported_inconvenience = true AND free text
(tags are only meaningful where text exists). Codes with <30 tagged
reporters excluded from estimation.

## Friction-type paths to SATISFACTION (sorted: most damaging first)
```
                      rval  Estimate  Est. Std   p-value  n_reporters_tagged  prevalence_among_reporters
          transport_access -0.257202 -0.123696       0.0                 511                    0.204155
opening_hours_availability -0.449484 -0.107022  0.000001                 104                    0.041550
   itinerary_fit_time_cost -0.348000 -0.063510  0.003431                  60                    0.023971
       cleanliness_comfort -0.227594 -0.048904  0.024055                  84                    0.033560
        food_amenities_gap -0.165830 -0.039484  0.068675                 104                    0.041550
        wayfinding_signage -0.054899 -0.010874  0.615807                  71                    0.028366
          waiting_crowding -0.007475 -0.002379  0.912531                 193                    0.077107
    accessibility_mobility  0.060491  0.018258  0.400907                 172                    0.068718
```

Negative Est. Std = that friction type predicts lower satisfaction among
friction reporters. These coefficients feed the nudge priority ranking
(scripts/rank_nudge_priorities.py).