# Chinese Social Media Analysis Readiness

This exploratory layer analyzes Chinese-language Xiaohongshu and Douyin recommendation text. It is not a nationality inference.

- Input directory: `/Users/andrewgreen/Repositories/andrew-verde/america-fukui-tourism/output/chinese_social_media_analysis/upstream_tourism_data_snapshot`
- Input files discovered: 1
- Rows before deduplication: 308
- Duplicate city/platform/text rows removed: 1
- Rows retained: 307
- Theme mix: {'ordinary': 168, 'travel': 96, 'fan': 43}
- Post-date precision mix: {'exact': 213, 'year_inferred': 80, 'relative_inferred': 14}

## Caveats

- Unit of analysis is one social-media search result row, currently title/text-level, not a full travel itinerary or confirmed visit.
- Chinese friction tags are substring keyword matches on titles and are directional only.
- Sentiment fields use a transparent keyword polarity scaffold, not VADER and not a validated Chinese sentiment model.
- Theme labels (fan / travel / ordinary) come from the companion tourism-data processed CSVs, joined on note id; rows without a label are `unclassified`.
- `post_date` is parsed from the Xiaohongshu author cell; `post_date_precision` marks exact vs year-inferred vs relative-inferred values (inference anchored to the scrape commit date).
- Side-project layer: these outputs are not thesis evidence.
