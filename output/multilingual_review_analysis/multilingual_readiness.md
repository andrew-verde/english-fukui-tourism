# Multilingual Cached Review Analysis

This analysis uses cached checkpoint files only. It does not call Google, Outscraper, or any paid collection API.

- Review date cutoff: `2024-06-01`
- Rows before deduplication: 6562
- Duplicate city/text rows removed: 526
- Rows retained: 6036
- Dropped by cutoff: 106
- Missing timestamps retained: 0
- Unparseable timestamps retained: 0

## Language Groups

| Language group | Reviews |
|---|---:|
| english | 919 |
| japanese | 4037 |
| other_non_english_non_japanese | 1040 |
| undetected_or_too_short | 40 |

## Caveats

- Review language is not reviewer nationality or residency.
- Japanese review friction uses the Japanese keyword codebook; English review friction uses the English codebook. Labels are mirrored, but keyword coverage is not a validated cross-language classifier.
- Other non-English/non-Japanese reviews are summarized by language and ratings only unless separate codebooks or translation are added.
- Very short reviews can be marked `undetected_or_too_short`; they are kept in the multilingual dataset but excluded from the other-language proxy segment.
