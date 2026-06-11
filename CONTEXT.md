# CONTEXT

Glossary of canonical terms for the Fukui tourism friction thesis. Terms here are
binding: code, documents, and discussion should use these words with these meanings.

## Core terms

**Friction** — Any obstacle a tourist encounters while planning or executing a visit
(transport access, wayfinding, opening hours, booking, etc.). Enumerated by the
12-code friction codebook. Distinct from *dissatisfaction* (an attitude); friction is
the experienced obstacle, dissatisfaction is a possible consequence.

**Friction tag** — A boolean assignment of one of the 12 friction codes to a unit of
text by the keyword tagger. A tag is a *measurement* of friction, not friction itself;
its validity is bounded by the tagger's evaluated precision/recall.

**Reported inconvenience** — The FTAS binary item (感じた / 感じなかった) asked of all
respondents. The only friction measure free of free-text selection bias; the canonical
friction-exposure variable for full-sample inference.

**Friction reporter** — A respondent with `reported_inconvenience = true`. The
population for conditional (Stage 2) analysis of *which* friction type matters.

**Nudge** — A low-cost informational intervention mapped from a friction code via
`config/nudge_mapping.yaml`. A nudge targets a friction; it does not target
satisfaction directly.

**Nudge pilot** — The browser experiment in `experiments/nudge-pilot/`. A small-N
system demonstration of nudge delivery and measurement, not a powered hypothesis test.

**Shinkansen shock** — The March 2024 Hokuriku Shinkansen extension to Fukui, treated
as an exogenous transport-friction-reduction event for quasi-experimental analysis.

## Evidence layers

**Observational layer (English reviews)** — 915 English-language Google Maps reviews
(Fukui / Kanazawa / Toyama). Exploratory, inbound-visitor signal. Unit: one review
(inference) or one sentence (description only). Side-project scope; minimal
statistical claims.

**Official survey layer (FTAS / merged Hokuriku)** — Respondent-level official survey
microdata: Fukui FTAS (n≈95k) and the merged tri-prefecture Hokuriku dataset
(n≈55k, Apr 2023–Feb 2026, CC-BY 4.0). Primary inference layer. Unit: one survey
respondent. Respondents are domestic Japanese tourists; not inbound.

**Aggregate layer** — JTA lodging statistics (monthly guest-nights incl. foreign
guest-nights, by area) and Google Business Profile metrics (daily, municipality
level). Objective behavioral outcomes; join key is municipality × time, never
facility.

## Population terms

**Japanese survey respondents** — FTAS/Hokuriku respondents. Never "Japanese
tourists" generally; never inferred nationality.

**English-language reviewers** — Authors of English Google Maps reviews. Never
"foreign tourists"; language is not nationality.
