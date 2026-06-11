PYTHON = .venv/bin/python3

.PHONY: help friction-all deep-review-all official-all fetch-fukui-data fetch-comparison-data fetch-google-maps-reviews fetch-metadata \
        fetch-official-fukui build-dataset build-mentions tag-codes summarize \
        build-ftas multilingual-reviews stats-official synth-official validate-japanese-tags presentation-figures stats synth sample-readiness test nudge-pilot-serve

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
	@echo "  make fetch-official-fukui    Fetch Code for Fukui official CSVs"
	@echo "  make build-ftas              Normalize + tag FTAS survey data"
	@echo "  make stats-official          Run official FTAS statistical validation"
	@echo "  make synth-official          Generate official-data statistical summary"
	@echo "  make validate-japanese-tags  Generate manual validation sample for Japanese friction tags"
	@echo ""
	@echo "Full pipeline:"
	@echo "  make friction-all            Run fetch-comparison-data through summarize"
	@echo "                               (assumes google_fukui.json already exists)"
	@echo "  make deep-review-all         Run deeper Google Maps review collection + full review analysis"
	@echo "  make official-all            Run Code for Fukui official-data pipeline"
	@echo ""
	@echo "Tests:"
	@echo "  make test                    Run pytest"
	@echo "  make nudge-pilot-serve       Serve the standalone nudge pilot app on localhost:8765"
	@echo ""

# Run full analysis pipeline (assumes google_fukui.json already exists)
friction-all: fetch-comparison-data fetch-metadata build-dataset build-mentions tag-codes summarize

deep-review-all: fetch-google-maps-reviews build-dataset build-mentions tag-codes summarize sample-readiness stats synth

official-all: fetch-official-fukui build-ftas stats-official synth-official

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

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest tests/ -v

nudge-pilot-serve:
	python3 -m http.server 8765 --directory experiments/nudge-pilot
