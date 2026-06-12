# Cross-Language Trends Readiness (Side Project)

Monthly volume and within-group sentiment for English Google reviewers, Japanese Google reviewers, and Chinese social-media commenters. Descriptive side-project comparison; not thesis evidence.

- Review rows (english/japanese, dated): 4956
- Chinese posts total: 105
- Chinese posts with a usable post_date: 105
- Chinese post_date precision mix: {'exact': 75, 'year_inferred': 26, 'relative_inferred': 4}

## Caveats

- Sentiment scales are group-specific: `rating_mean` is the Google 1-5 star mean (english/japanese); `sentiment_norm_mean` is the Chinese keyword-lexicon polarity mean in [0,1]. Levels are NOT comparable across groups; only within-group trajectories are interpretable.
- Chinese text is title-level and volumes are small; treat monthly Chinese cells as directional interest signals, not rates.
- Chinese `post_date` values flagged `year_inferred` or `relative_inferred` were reconstructed relative to the scrape date (see chinese_social_readiness.md).
- Group membership is content language, not nationality.
- No significance testing is run on these series by design (descriptive scope).
