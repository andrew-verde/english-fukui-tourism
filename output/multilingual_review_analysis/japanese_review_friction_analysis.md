# Japanese Review Friction Analysis

This report uses cached Google review checkpoints only. It compares detected Japanese-language reviews with detected English-language reviews; language is not reviewer nationality.

Friction labels are shown as English label (Japanese translation). Rates use review-level denominators so English and Japanese review samples can be compared directly.

## Top Japanese Friction Points by City

### Fukui

- Accessibility / Mobility (アクセシビリティ・移動しやすさ): 158 / 1800 reviews (8.78%).
- Waiting / Crowding (待ち時間・混雑): 74 / 1800 reviews (4.11%).
- Opening Hours / Availability (営業時間・利用可否): 34 / 1800 reviews (1.89%).
- Cleanliness / Comfort (清潔さ・快適性): 21 / 1800 reviews (1.17%).
- Booking / Ticketing (予約・チケット・決済): 14 / 1800 reviews (0.78%).
- Transport / Access (交通・アクセス): 13 / 1800 reviews (0.72%).

### Kanazawa

- Waiting / Crowding (待ち時間・混雑): 58 / 1050 reviews (5.52%).
- Accessibility / Mobility (アクセシビリティ・移動しやすさ): 39 / 1050 reviews (3.71%).
- Cleanliness / Comfort (清潔さ・快適性): 20 / 1050 reviews (1.91%).
- Opening Hours / Availability (営業時間・利用可否): 13 / 1050 reviews (1.24%).
- Booking / Ticketing (予約・チケット・決済): 11 / 1050 reviews (1.05%).
- English Information Gap (英語・多言語情報不足): 10 / 1050 reviews (0.95%).

### Toyama

- Waiting / Crowding (待ち時間・混雑): 50 / 1187 reviews (4.21%).
- Accessibility / Mobility (アクセシビリティ・移動しやすさ): 33 / 1187 reviews (2.78%).
- Opening Hours / Availability (営業時間・利用可否): 22 / 1187 reviews (1.85%).
- Cleanliness / Comfort (清潔さ・快適性): 11 / 1187 reviews (0.93%).
- Transport / Access (交通・アクセス): 8 / 1187 reviews (0.67%).
- Wayfinding / Signage (案内・サイン): 8 / 1187 reviews (0.67%).

## English vs Japanese Review Comparison

Fisher exact p-values are used as the main comparison because some English review cells are sparse. BH correction is applied across all city-code comparisons.

- Kanazawa — Accessibility / Mobility (アクセシビリティ・移動しやすさ): English 1/536 (0.19%), Japanese 39/1050 (3.71%), higher in Japanese by 3.53 pp; Fisher p_BH=5.92e-05.
- Kanazawa — Cleanliness / Comfort (清潔さ・快適性): English 0/536 (0.00%), Japanese 20/1050 (1.91%), higher in Japanese by 1.91 pp; Fisher p_BH=0.00514.
- Fukui — Waiting / Crowding (待ち時間・混雑): English 0/214 (0.00%), Japanese 74/1800 (4.11%), higher in Japanese by 4.11 pp; Fisher p_BH=0.00514.
- Fukui — Transport / Access (交通・アクセス): English 8/214 (3.74%), Japanese 13/1800 (0.72%), higher in English by 3.02 pp; Fisher p_BH=0.00614.
- Fukui — Price / Value (価格・価値): English 6/214 (2.80%), Japanese 6/1800 (0.33%), higher in English by 2.47 pp; Fisher p_BH=0.00614.
- Fukui — Accessibility / Mobility (アクセシビリティ・移動しやすさ): English 6/214 (2.80%), Japanese 158/1800 (8.78%), higher in Japanese by 5.97 pp; Fisher p_BH=0.00795.
- Kanazawa — Price / Value (価格・価値): English 9/536 (1.68%), Japanese 3/1050 (0.29%), higher in English by 1.39 pp; Fisher p_BH=0.0214.
- Fukui — Itinerary Fit / Time & Cost (旅程適合・時間コスト): English 5/214 (2.34%), Japanese 7/1800 (0.39%), higher in English by 1.95 pp; Fisher p_BH=0.0246.
- Fukui — Opening Hours / Availability (営業時間・利用可否): English 9/214 (4.21%), Japanese 34/1800 (1.89%), higher in English by 2.32 pp; Fisher p_BH=0.162.
- Fukui — Food / Amenities Gap (飲食・設備不足): English 1/214 (0.47%), Japanese 0/1800 (0.00%), higher in English by 0.47 pp; Fisher p_BH=0.383.

## Caveats

- The Japanese and English codebooks are mirrored by code label, but they are keyword rules rather than a validated cross-language classifier.
- Japanese substring matching can overcount broad terms such as stairs, signs, or English unless manually validated.
- English review counts are much smaller than Japanese review counts, so sparse-cell p-values and effect sizes should be interpreted descriptively.
