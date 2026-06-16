const DATA_URL = "./data/scenario_data.json";

const state = {
  payload: null,
  selectedCode: null,
};

const els = {
  dataStatus: document.querySelector("#dataStatus"),
  claimBoundary: document.querySelector("#claimBoundary"),
  frictionSelect: document.querySelector("#frictionSelect"),
  effectiveness: document.querySelector("#effectiveness"),
  effectivenessValue: document.querySelector("#effectivenessValue"),
  reach: document.querySelector("#reach"),
  reachValue: document.querySelector("#reachValue"),
  showAllCodes: document.querySelector("#showAllCodes"),
  includeNonSignificant: document.querySelector("#includeNonSignificant"),
  intentionShift: document.querySelector("#intentionShift"),
  ceilingValue: document.querySelector("#ceilingValue"),
  prevalenceValue: document.querySelector("#prevalenceValue"),
  frictionTitle: document.querySelector("#frictionTitle"),
  journeyStage: document.querySelector("#journeyStage"),
  nudgeType: document.querySelector("#nudgeType"),
  semPath: document.querySelector("#semPath"),
  reporterCount: document.querySelector("#reporterCount"),
  interventionText: document.querySelector("#interventionText"),
  formulaLabel: document.querySelector("#formulaLabel"),
  rankList: document.querySelector("#rankList"),
  sourceList: document.querySelector("#sourceList"),
};

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function signed(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(4)}`;
}

function assumptions() {
  return {
    effectiveness: Number(els.effectiveness.value) / 100,
    reach: Number(els.reach.value) / 100,
  };
}

function scenarioValue(item) {
  const { effectiveness, reach } = assumptions();
  return item.recoverable_intention_ceiling * effectiveness * reach;
}

function visibleCodes() {
  const codes = state.payload.sem.friction_codes;
  const includeWeak = els.includeNonSignificant.checked;
  if (includeWeak) return codes;
  return codes.filter((item) => item.p_value <= 0.05 && item.sem_path_to_satisfaction_std < 0);
}

function selectedItem() {
  return state.payload.sem.friction_codes.find((item) => item.code === state.selectedCode)
    || state.payload.sem.friction_codes[0];
}

function updateControls() {
  els.effectivenessValue.textContent = `${els.effectiveness.value}%`;
  els.reachValue.textContent = `${els.reach.value}%`;
}

function renderSelected() {
  const item = selectedItem();
  const value = scenarioValue(item);

  els.intentionShift.textContent = signed(value);
  els.ceilingValue.textContent = item.recoverable_intention_ceiling.toFixed(4);
  els.prevalenceValue.textContent = pct(item.prevalence_among_reporters);
  els.frictionTitle.textContent = item.label;
  els.journeyStage.textContent = item.journey_stage;
  els.nudgeType.textContent = item.nudge_type;
  els.semPath.textContent = `${signed(item.sem_path_to_satisfaction_std)} to satisfaction; p=${item.p_value.toPrecision(3)}`;
  els.reporterCount.textContent = item.n_reporters_tagged.toLocaleString();
  els.interventionText.textContent = item.example_intervention;
}

function renderRanking() {
  const codes = visibleCodes()
    .map((item) => ({ ...item, scenario: scenarioValue(item) }))
    .sort((a, b) => b.scenario - a.scenario);
  const maxValue = Math.max(...codes.map((item) => item.scenario), 0.000001);
  const maybeLimit = els.showAllCodes.checked ? codes : codes.slice(0, 5);

  els.formulaLabel.textContent = `effectiveness ${els.effectiveness.value}% x reach ${els.reach.value}%`;
  els.rankList.replaceChildren(
    ...maybeLimit.map((item) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "rank-item";
      row.setAttribute("aria-label", `Select ${item.label}`);
      row.addEventListener("click", () => {
        state.selectedCode = item.code;
        els.frictionSelect.value = item.code;
        render();
      });

      const name = document.createElement("div");
      name.className = "rank-name";
      name.textContent = item.label;

      const track = document.createElement("div");
      track.className = "bar-track";
      const fill = document.createElement("div");
      fill.className = "bar-fill";
      fill.style.width = `${Math.max((item.scenario / maxValue) * 100, 1)}%`;
      track.append(fill);

      const value = document.createElement("div");
      value.className = "rank-value";
      value.textContent = signed(item.scenario);

      row.append(name, track, value);
      return row;
    })
  );
}

function renderSources() {
  const cards = state.payload.public_sources.map((source) => {
    const card = document.createElement("article");
    card.className = "source-card";

    const link = document.createElement("a");
    link.href = source.repo;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = source.name;

    const text = document.createElement("p");
    text.textContent = source.role;

    card.append(link, text);
    return card;
  });
  els.sourceList.replaceChildren(...cards);
}

function render() {
  updateControls();
  renderSelected();
  renderRanking();
}

async function init() {
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(`Could not load ${DATA_URL}`);
  state.payload = await response.json();
  state.selectedCode = state.payload.sem.friction_codes[0].code;

  els.claimBoundary.textContent = state.payload.interpretation.claim_boundary;
  els.dataStatus.textContent = `Seeded ${state.payload.generated_on}`;
  els.frictionSelect.replaceChildren(
    ...state.payload.sem.friction_codes.map((item) => {
      const option = document.createElement("option");
      option.value = item.code;
      option.textContent = item.label;
      return option;
    })
  );

  els.effectiveness.value = Math.round(state.payload.interpretation.default_effectiveness * 100);
  els.reach.value = Math.round(state.payload.interpretation.default_reach * 100);

  els.frictionSelect.addEventListener("change", () => {
    state.selectedCode = els.frictionSelect.value;
    render();
  });
  [els.effectiveness, els.reach, els.showAllCodes, els.includeNonSignificant].forEach((control) => {
    control.addEventListener("input", render);
    control.addEventListener("change", render);
  });

  renderSources();
  render();
}

init().catch((error) => {
  els.dataStatus.textContent = "Data load failed";
  els.claimBoundary.textContent = error.message;
});
