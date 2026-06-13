# Review Sample Readiness

Input: `/home/andrewgreen/Repositories/andrew-verde/america-fukui-tourism/output/friction_analysis/reviews_unified.csv`
Total reviews: **915**

## City Counts

| City | Reviews | Additional needed for target |
|---|---:|---:|
| Fukui | 213 | 0 |
| Kanazawa | 533 | 0 |
| Toyama | 169 | 0 |

## City x Theme Readiness (All Themes)

Themed reviews: **402**
Minimum expected cell count: **2.943**
Cells below target (5.0): **2**
Additional themed reviews estimated for target: **282**

## City x Theme Readiness (Shared Themes)

Shared themes exclude `Dinosaur`, which is treated as a Fukui-specific destination theme rather than a comparable cross-city category.
Shared themed reviews: **389**
Minimum expected cell count: **9.486**
Cells below target (5.0): **0**

## Gates

- `all_cities_present`: PASS
- `min_reviews_per_city_met`: PASS
- `shared_city_x_theme_expected_counts_met`: PASS

Ready for stronger city-level inference: **YES**

This audit checks sample adequacy only. It does not remove the need for exploratory framing, source-bias caveats, or manual review of keyword-code precision.
