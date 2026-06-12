# Chinese Social Media Analysis Readiness

This layer treats Xiaohongshu notes and Douyin videos as Chinese-language recommendation text, analogous to the role Google reviews play for English-language review analysis. It is not a nationality inference.

- Input directory: `/home/andrewgreen/Repositories/external/tourism-data`
- Input files discovered: 1
- Rows before deduplication: 106
- Duplicate city/platform/text rows removed: 1
- Rows retained: 105
- Theme mix: {'ordinary': 65, 'fan': 22, 'travel': 18}
- Post-date precision mix: {'exact': 75, 'year_inferred': 26, 'relative_inferred': 4}

## Caveats

- Unit of analysis is one social-media search result row, currently title/text-level, not a full travel itinerary or confirmed visit.
- Chinese friction tags are substring keyword matches on titles; title-level rates understate friction relative to full-text review rates and are directional only.
- Sentiment fields use a transparent keyword polarity scaffold, not VADER and not a validated Chinese sentiment model.
- Compare Chinese social-media rates with Google review-language rates descriptively because source platform behavior and text length differ.
- Theme labels (fan / travel / ordinary) come from the companion tourism-data processed CSVs, joined on note id; rows without a label are `unclassified`.
- `post_date` is parsed from the Xiaohongshu author cell; `post_date_precision` marks exact vs year-inferred vs relative-inferred values (inference anchored to the scrape commit date).
- Side-project layer: these outputs feed the cross-language trends comparison only and are not thesis evidence.
