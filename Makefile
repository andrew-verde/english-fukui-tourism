PYTHON = .venv/bin/python3

.PHONY: help friction-all deep-review-all official-all fetch-fukui-data fetch-comparison-data fetch-google-maps-reviews fetch-metadata \
        fetch-official-fukui build-dataset build-mentions tag-codes summarize \
        build-ftas multilingual-reviews chinese-social cross-language-trends stats-official synth-official validate-japanese-tags presentation-figures stats synth sample-readiness test nudge-pilot-serve \
        gold-set gold-set-eval fetch-hokuriku-merged hokuriku-did-audit data-manifest \
        fetch-estat fetch-estat-list fetch-national-direct accommodation-panel \
        hokuriku-did-event-study sem-ftas nudge-ranking reproduce-submission

help:
	@echo ""
	@echo "Focused Friction Analysis Pipeline"
	@echo "==================================="
	@echo ""
	@echo "Data collection:"
	@echo "  make fetch-fukui-data        Fetch Fukui Google Places reviews"
	@echo "  make fetch-comparison-data   Fetch Kanazawa + Toyama reviews"
	@echo "  make fetch-google-maps-reviews Fetch deeper Google Maps reviews via Outscraper"
	@echo "  make fetch-metadata          Fetch POI types from Google Places Details"
	@echo ""
	@echo "Analysis (no API keys needed once checkpoints exist):"
	@echo "  make build-dataset           Build unified reviews_unified.csv"
	@echo "  make build-mentions          Split reviews into sentence-level mentions"
	@echo "  make tag-codes               Tag reviews + mentions with friction codes"
	@echo "  make summarize               Generate summary CSVs and plots"
	@echo "  make sample-readiness        Audit sample size/statistical readiness"
	@echo "  make presentation-figures    Generate presentation figure files"
	@echo "  make stats                   Run SR statistical validation"
	@echo "  make synth                   Generate output/statistical_summary.md"
	@echo "  make multilingual-reviews    Build cached Japanese/other-language review comparison suite"
	@echo ""
	@echo "Cross-language trends side project (separate from thesis pipeline):"
	@echo "  make chinese-social          Build Chinese Xiaohongshu/Douyin layer from tourism-data scrapes"
	@echo "  make cross-language-trends   Build EN/JP/CN monthly volume + sentiment trend tables"
	@echo "  make fetch-official-fukui    Fetch Code for Fukui official CSVs"
	@echo "  make build-ftas              Normalize + tag FTAS survey data"
	@echo "  make stats-official          Run official FTAS statistical validation"
	@echo "  make synth-official          Generate official-data statistical summary"
	@echo "  make validate-japanese-tags  Generate manual validation sample for Japanese friction tags"
	@echo "  make data-manifest           Generate row-count/schema/hash manifest for key datasets"
	@echo ""
	@echo "Gold-set tagger evaluation:"
	@echo "  make gold-set                Build blind coder sheets + key in output/gold_set/"
	@echo "  make gold-set-eval           Score coder sheets: kappa + tagger precision/recall"
	@echo ""
	@echo "Hokuriku merged survey / Shinkansen DiD:"
	@echo "  make fetch-hokuriku-merged   Download merged tri-prefecture survey microdata (CC-BY)"
	@echo "  make hokuriku-did-audit      Run DiD feasibility audit + parallel-trends plot"
	@echo "  make hokuriku-did-event-study Thesis DiD: event study, robustness, clustered SEs"
	@echo ""
	@echo "National supplementary data (JNTO/JTA/MLIT/JR West):"
	@echo "  make fetch-estat             Pull e-Stat datasets (needs ESTAT_APP_ID env var)"
	@echo "  make fetch-estat-list        Discovery only: list available e-Stat tables"
	@echo "  make fetch-national-direct   Download JTA accommodation Excels + JR West press PDFs"
	@echo "  make accommodation-panel     Build prefecture-month overnight-stay panel CSV"
	@echo ""
	@echo "SEM + nudge ranking (primary thesis analyses):"
	@echo "  make sem-ftas                Two-stage SEM on deduplicated FTAS respondents"
	@echo "  make nudge-ranking           Evidence-weighted nudge priority table"
	@echo ""
	@echo "Full pipeline:"
	@echo "  make friction-all            Run fetch-comparison-data through summarize"
	@echo "                               (assumes google_fukui.json already exists)"
	@echo "  make deep-review-all         Run deeper Google Maps review collection + full review analysis"
	@echo "  make official-all            Run Code for Fukui official-data pipeline"
	@echo "  make reproduce-submission    Run no-network reviewer reproduction path"
	@echo ""
	@echo "Tests:"
	@echo "  make test                    Run pytest"
	@echo "  make nudge-pilot-serve       Serve the standalone nudge pilot app on localhost:8765"
	@echo ""

# Run full analysis pipeline (assumes google_fukui.json already exists)
friction-all: fetch-comparison-data fetch-metadata build-dataset build-mentions tag-codes summarize

deep-review-all: fetch-google-maps-reviews build-dataset build-mentions tag-codes summarize sample-readiness stats synth

official-all: fetch-official-fukui build-ftas stats-official synth-official

reproduce-submission: test build-dataset build-mentions tag-codes summarize sample-readiness stats synth build-ftas stats-official synth-official sem-ftas nudge-ranking hokuriku-did-event-study data-manifest

# ── Data collection ───────────────────────────────────────────────────────────

fetch-fukui-data:
	$(PYTHON) scripts/pull.py

fetch-comparison-data:
	$(PYTHON) scripts/fetch_comparison_city_data.py

fetch-google-maps-reviews:
	$(PYTHON) scripts/fetch_google_maps_reviews.py --all

fetch-metadata:
	$(PYTHON) scripts/fetch_poi_metadata.py

fetch-official-fukui:
	$(PYTHON) scripts/fetch_code4fukui_data.py

# ── Analysis ──────────────────────────────────────────────────────────────────

build-dataset:
	$(PYTHON) scripts/build_analysis_dataset.py

build-ftas:
	$(PYTHON) scripts/build_ftas_survey_dataset.py

build-mentions:
	$(PYTHON) scripts/build_mentions_dataset.py

tag-codes:
	$(PYTHON) scripts/auto_tag_friction_codes.py

summarize:
	$(PYTHON) scripts/generate_friction_summaries.py

presentation-figures:
	$(PYTHON) scripts/generate_presentation_figures.py

stats:
	$(PYTHON) scripts/statistical_validation.py

synth:
	$(PYTHON) scripts/synthesis_pipeline.py

sample-readiness:
	$(PYTHON) scripts/audit_review_sample_readiness.py

multilingual-reviews:
	$(PYTHON) scripts/build_multilingual_review_dataset.py

# ── Cross-language trends side project (not part of any thesis chain) ────────

chinese-social:
	$(PYTHON) scripts/build_chinese_social_media_dataset.py

cross-language-trends:
	$(PYTHON) scripts/build_cross_language_trends.py

data-manifest:
	$(PYTHON) scripts/generate_data_manifest.py

stats-official:
	$(PYTHON) scripts/statistical_validation_official.py

synth-official:
	$(PYTHON) scripts/synthesis_official_pipeline.py

validate-japanese-tags:
	$(PYTHON) scripts/build_japanese_friction_validation_sample.py

gold-set:
	$(PYTHON) scripts/build_gold_set.py

gold-set-eval:
	$(PYTHON) scripts/evaluate_gold_set.py

fetch-hokuriku-merged:
	$(PYTHON) scripts/fetch_hokuriku_merged.py

fetch-estat:
	$(PYTHON) scripts/fetch_estat_data.py

fetch-estat-list:
	$(PYTHON) scripts/fetch_estat_data.py --list-only

fetch-national-direct:
	$(PYTHON) scripts/fetch_national_direct.py

accommodation-panel:
	$(PYTHON) scripts/build_accommodation_panel.py

hokuriku-did-audit:
	$(PYTHON) scripts/hokuriku_did_audit.py

hokuriku-did-event-study:
	$(PYTHON) scripts/hokuriku_did_event_study.py

sem-ftas:
	$(PYTHON) scripts/sem_ftas.py

nudge-ranking:
	$(PYTHON) scripts/rank_nudge_priorities.py

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest tests/ -v

nudge-pilot-serve:
	python3 -m http.server 8765 --directory experiments/nudge-pilot
