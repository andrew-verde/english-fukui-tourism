# Thesis Readiness Assessment

## Defense Readiness
Status: **mostly defense-ready as an expanded mixed-source observational analysis**, with caveats.

The added official survey layer fixes the main weakness of the original Google-review-only analysis: statistical power. The original English-language Google review sample remains too sparse for strong inferential friction claims, but the official Japanese tourist survey layer provides respondent-level tests with large samples.

## What Now Passes Muster
- Official Fukui survey n: 95,422 respondent rows.
- Official friction text is significantly associated with lower/shifted satisfaction or NPS outcomes for: overall_satisfaction_score, transport_satisfaction_score, nps.
- Fukui vs Ishikawa official survey friction tests surviving BH correction: 9 of 12 friction codes.
- Fukui vs Ishikawa Kanazawa-area official survey friction tests surviving BH correction: 10 of 12 friction codes.
- Shinkansen survey mode shift p-value: <0.001.
- Reservation demand context shows statistically detectable post-extension changes for at least some daily demand measures.

## Remaining Gaps
- The Japanese friction codebook is keyword-based and needs manual validation on a sampled set of FTAS/Ishikawa comments before final defense claims.
- English Google review friction remains descriptive because counts are sparse; present it as English-language perception evidence, not as the main inferential layer.
- Fukui and Ishikawa official survey instruments are similar but not identical. Prefecture comparisons should be framed as harmonized official-survey comparisons, not perfectly identical measurement.
- Current tests show statistical significance partly because official survey n is large; emphasize effect sizes and rates, not p-values alone.

## Recommended Dataset Rounding
1. Add a 100-200 row manual validation sample for Japanese friction tags with precision estimates by code.
2. Add a curated area crosswalk for Fukui POIs, FTAS areas, and Ishikawa facilities so area-level triangulation is defensible.
3. Use people-flow only for Tojinbo and Fukui Station as contextual congestion/event evidence, not as a core inferential pillar.
4. If more English-language evidence is needed, expand Google Maps review POIs or add TripAdvisor/Google review pulls with the same date/language filters, but keep reviewer nationality unspecified.
