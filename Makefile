PYTHON = .venv/bin/python3

.PHONY: help official-all fetch-official-fukui build-ftas stats-official \
	synth-official chinese-social fetch-hokuriku-merged hokuriku-did-audit \
	hokuriku-did-event-study fetch-estat fetch-estat-list fetch-national-direct \
	accommodation-panel sem-ftas nudge-ranking result-charts data-manifest \
	reproduce-submission test nudge-pilot-serve friction-simulator-data \
	friction-simulator-serve claim-registry publication-check

help:
	@echo "Fukui official-data tourism analysis"
	@echo ""
	@echo "  make official-all              Build and analyze official FTAS data"
	@echo "  make sem-ftas                  Run two-stage FTAS SEM"
	@echo "  make nudge-ranking             Build evidence-weighted nudge ranking"
	@echo "  make friction-simulator-data   Build static data for SEM scenario simulator"
	@echo "  make friction-simulator-serve  Serve friction simulator on localhost:8766"
	@echo "  make claim-registry            Build paper-facing claim registry"
	@echo "  make publication-check         Check publication readiness"
	@echo "  make hokuriku-did-event-study  Run thesis DiD/event study"
	@echo "  make accommodation-panel      Build JTA overnight-stay panel"
	@echo "  make result-charts             Generate official-data charts"
	@echo "  make reproduce-submission      Run no-network reproduction path"
	@echo "  make test                      Run maintained tests"

official-all: build-ftas stats-official synth-official

reproduce-submission: test build-ftas stats-official synth-official sem-ftas nudge-ranking hokuriku-did-event-study data-manifest

fetch-official-fukui:
	$(PYTHON) scripts/fetch_code4fukui_data.py

build-ftas:
	$(PYTHON) scripts/build_ftas_survey_dataset.py

stats-official:
	$(PYTHON) scripts/statistical_validation_official.py

synth-official:
	$(PYTHON) scripts/synthesis_official_pipeline.py

claim-registry:
	$(PYTHON) scripts/build_claim_registry.py

publication-check:
	$(PYTHON) scripts/check_publication_readiness.py

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

accommodation-panel:
	$(PYTHON) scripts/build_accommodation_panel.py

sem-ftas:
	$(PYTHON) scripts/sem_ftas.py

nudge-ranking:
	$(PYTHON) scripts/rank_nudge_priorities.py

result-charts:
	$(PYTHON) scripts/generate_result_charts.py

data-manifest:
	$(PYTHON) scripts/generate_data_manifest.py

friction-simulator-data:
	$(PYTHON) scripts/build_friction_simulator_data.py

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest tests/ -v

nudge-pilot-serve:
	python3 -m http.server 8765 --directory experiments/nudge-pilot

friction-simulator-serve:
	python3 -m http.server 8766 --directory experiments/friction-simulator
