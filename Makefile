PYTHON = .venv/bin/python3

.PHONY: help fetch official-all fetch-official-fukui build-ftas stats-official \
	synth-official chinese-social fetch-hokuriku-merged hokuriku-did-audit \
	hokuriku-did-event-study fetch-estat fetch-estat-list fetch-national-direct \
	fetch-ff-data fetch-japan-kanko-stat accommodation-panel ff-data-panel japan-kanko-panel synthetic-control \
	vision-descriptive sem-ftas nudge-ranking result-charts data-manifest \
	reproduce-submission test nudge-pilot-serve

help:
	@echo "Fukui official-data tourism analysis"
	@echo ""
	@echo "  make official-all              Build and analyze official FTAS data"
	@echo "  make fetch                     Reconstruct checksum-pinned raw data"
	@echo "  make sem-ftas                  Run two-stage FTAS SEM"
	@echo "  make nudge-ranking             Build evidence-weighted nudge ranking"
	@echo "  make hokuriku-did-event-study  Run thesis DiD/event study"
	@echo "  make fetch-ff-data             Fetch MLIT FF-DATA API records"
	@echo "  make accommodation-panel      Build JTA overnight-stay panel"
	@echo "  make ff-data-panel             Build FF-DATA quarterly flow panel"
	@echo "  make fetch-japan-kanko-stat    Fetch pinned municipal visitor panel"
	@echo "  make synthetic-control         Run Fukui City synthetic control"
	@echo "  make result-charts             Generate official-data charts"
	@echo "  make reproduce-submission      Run no-network reproduction path"
	@echo "  make test                      Run maintained tests"

official-all: build-ftas stats-official synth-official

fetch: fetch-official-fukui fetch-japan-kanko-stat

reproduce-submission: test build-ftas stats-official synth-official sem-ftas nudge-ranking hokuriku-did-event-study data-manifest

fetch-official-fukui:
	$(PYTHON) scripts/fetch_code4fukui_data.py

build-ftas:
	$(PYTHON) scripts/build_ftas_survey_dataset.py

stats-official:
	$(PYTHON) scripts/statistical_validation_official.py

synth-official:
	$(PYTHON) scripts/synthesis_official_pipeline.py

chinese-social:
	$(PYTHON) scripts/build_chinese_social_media_dataset.py

fetch-hokuriku-merged:
	$(PYTHON) scripts/fetch_hokuriku_merged.py

hokuriku-did-audit:
	$(PYTHON) scripts/hokuriku_did_audit.py

hokuriku-did-event-study:
	$(PYTHON) scripts/hokuriku_did_event_study.py

fetch-estat:
	$(PYTHON) scripts/fetch_estat_data.py

fetch-estat-list:
	$(PYTHON) scripts/fetch_estat_data.py --list-only

fetch-national-direct:
	$(PYTHON) scripts/fetch_national_direct.py

fetch-ff-data:
	$(PYTHON) scripts/fetch_ff_data.py

accommodation-panel:
	$(PYTHON) scripts/build_accommodation_panel.py

ff-data-panel:
	$(PYTHON) scripts/build_ff_data_panel.py

fetch-japan-kanko-stat:
	$(PYTHON) scripts/fetch_japan_kanko_stat.py

japan-kanko-panel:
	$(PYTHON) scripts/build_japan_kanko_panel.py

synthetic-control:
	$(PYTHON) scripts/synthetic_control_fukui.py

vision-descriptive:
	$(PYTHON) scripts/build_resident_vision.py

sem-ftas:
	$(PYTHON) scripts/sem_ftas.py

nudge-ranking:
	$(PYTHON) scripts/rank_nudge_priorities.py

result-charts:
	$(PYTHON) scripts/generate_result_charts.py

data-manifest:
	$(PYTHON) scripts/generate_data_manifest.py

test:
	$(PYTHON) -m pytest tests/ -v

nudge-pilot-serve:
	python3 -m http.server 8765 --directory experiments/nudge-pilot
