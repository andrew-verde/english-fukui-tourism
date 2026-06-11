# Friction Coding Guide / フリクション・コーディングガイド

Read each survey free-text response and mark **1** in every friction code
column that applies (multiple codes allowed). If no friction is described,
mark **1** in `no_friction`. Use `notes` for anything ambiguous.

各自由記述を読み、当てはまるフリクションコードの列すべてに **1** を記入して
ください（複数可）。フリクションが書かれていない場合は `no_friction` に **1**。
迷った場合は `notes` にメモしてください。

Judge what the respondent **experienced**, not the keywords used — the point
of this exercise is to check the keyword system against human judgment, so do
not try to guess what a machine would do.

| Code | Label | 説明の目安 |
|------|-------|-----------|
| `transport_access` | Transport / Access | 例: アクセスが悪、交通の便が悪、交通が不便、公共交通… |
| `wayfinding_signage` | Wayfinding / Signage | 例: 案内がわかりにく、案内表示、表示がわかりにく、看板… |
| `english_information_gap` | English Information Gap | 例: 英語、外国語、多言語、翻訳… |
| `staff_communication` | Staff Communication | 例: 接客が悪、接客に不満、対応が悪、スタッフの対応… |
| `booking_ticketing` | Booking / Ticketing | 例: 予約でき、予約が取れ、予約が必要、チケットが買え… |
| `waiting_crowding` | Waiting / Crowding | 例: 混雑、混んで、人が多、行列… |
| `price_value` | Price / Value | 例: 料金が高、値段が高、価格が高、割高… |
| `cleanliness_comfort` | Cleanliness / Comfort | 例: 汚い、不衛生、清潔でない、清潔感がない… |
| `opening_hours_availability` | Opening Hours / Availability | 例: 休み、休館、定休日、閉まって… |
| `itinerary_fit_time_cost` | Itinerary Fit / Time & Cost | 例: 時間が足り、時間がかか、見るものが少な、何もない… |
| `accessibility_mobility` | Accessibility / Mobility | 例: 階段、段差、坂、急な坂… |
| `food_amenities_gap` | Food / Amenities Gap | 例: 飲食店が少な、飲食店がない、食事するところが少な、食事するところがない… |

Notes:
- A complaint can carry several codes (e.g. 「駅から遠いしバスも少ない」 →
  `transport_access` only; 「案内も分かりにくい」が加われば `wayfinding_signage` も).
- Positive comments, suggestions with no experienced problem, and empty
  pleasantries are `no_friction`.
- Suggestions that imply an experienced gap (「飲食店が少ないので増やしてほしい」)
  DO count as friction (`food_amenities_gap`).