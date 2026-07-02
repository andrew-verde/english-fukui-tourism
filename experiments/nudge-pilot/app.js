const STORAGE_KEY = "fukui_nudge_pilot_sessions";
const CURRENT_KEY = "fukui_nudge_pilot_current";
const API_HEALTH_ENDPOINT = "/api/health";
const API_SUBMIT_ENDPOINT = "/api/submit";
const API_ASSIGN_ENDPOINT = "/api/assign";
const TASK_PAIRS = [
  [0, 1],
  [1, 0],
  [0, 2],
  [2, 0],
  [1, 2],
  [2, 1]
];

let config;
let state;
let stepIndex = 0;
let stepStartedAt = Date.now();
let remoteApiAvailable = false;

const app = document.getElementById("app");
const stepLabel = document.getElementById("stepLabel");
const progressBar = document.getElementById("progressBar");

const steps = [
  "consent",
  "background",
  "task_0",
  "survey_0",
  "task_1",
  "survey_1",
  "final",
  "export"
];

init();

async function init() {
  config = await fetch("study-config.json").then((response) => response.json());
  remoteApiAvailable = await checkRemoteApi();
  state = loadCurrentState() || createState();
  ensureTaskAssignment();
  stepIndex = state.stepIndex || 0;
  render();
}

function createState() {
  const sessionId = `pilot_${new Date().toISOString().replace(/[-:.TZ]/g, "")}_${cryptoRandom(6)}`;
  const newState = {
    study_id: config.study_id,
    version: config.version,
    session_id: sessionId,
    assigned_condition: "",
    assignment_method: "",
    assignment_stratum: "",
    assigned_task_ids: [],
    task_order: [],
    started_at: new Date().toISOString(),
    completed_at: "",
    consent: false,
    background: {},
    tasks: {},
    surveys: {},
    final: {},
    events: [],
    remote_submission: {
      status: "not_started",
      submitted_at: "",
      response_id: "",
      message: ""
    },
    stepIndex: 0
  };
  state = newState;
  ensureTaskAssignment();
  return newState;
}

function hashString(seed) {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function ensureTaskAssignment() {
  if (state.assigned_task_ids?.length === 2 && state.task_order?.length === 2) return;
  const pairIndex = hashString(`${state.session_id}|tasks`) % TASK_PAIRS.length;
  state.task_order = TASK_PAIRS[pairIndex].slice();
  state.assigned_task_ids = state.task_order.map((index) => config.tasks[index].id);
}

function getAssignedTasks() {
  ensureTaskAssignment();
  return state.assigned_task_ids.map((taskId) => (
    config.tasks.find((task) => task.id === taskId)
  ));
}

async function assignCondition() {
  if (state.assigned_condition) return;
  const stratum = `${state.background.fukui_familiarity}|${state.background.japan_travel_experience}`;
  state.assignment_stratum = stratum;
  try {
    const response = await fetch(API_ASSIGN_ENDPOINT, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        session_id: state.session_id,
        stratum
      })
    });
    const result = await response.json().catch(() => ({}));
    const validCondition = config.conditions.some((condition) => condition.id === result.condition);
    if (!response.ok || !validCondition) {
      throw new Error(result.error || `Assignment failed with HTTP ${response.status}`);
    }
    state.assigned_condition = result.condition;
    state.assignment_method = "server_block";
  } catch (_error) {
    const index = hashString(`${state.session_id}|${stratum}`) % config.conditions.length;
    state.assigned_condition = config.conditions[index].id;
    state.assignment_method = "hash_fallback";
  }
  saveCurrentState();
}

function cryptoRandom(length) {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function render(options = {}) {
  stepStartedAt = Date.now();
  state.stepIndex = stepIndex;
  saveCurrentState();
  updateProgress();

  const step = steps[stepIndex];
  if (step === "consent") renderConsent();
  if (step === "background") renderBackground();
  if (step.startsWith("task_")) renderTask(Number(step.split("_")[1]));
  if (step.startsWith("survey_")) renderSurvey(Number(step.split("_")[1]));
  if (step === "final") renderFinalQuestions();
  if (step === "export") renderExport();

  bindValidationClearers();
  if (options.resetScroll) resetPageScroll();
}

function updateProgress() {
  stepLabel.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
  progressBar.style.width = `${Math.round((stepIndex / (steps.length - 1)) * 100)}%`;
}

function renderConsent() {
  app.innerHTML = `
    <h2>Study Consent</h2>
    <p>This pilot asks you to complete short tourism-planning tasks and answer planning-experience questions. It does not ask for your name, email, or precise location.</p>
    <div class="callout">
      <p><strong>Research use:</strong> responses are intended for pilot analysis of whether destination-planning nudges change information clarity, perceived friction, planning confidence, and visit intention.</p>
      <p class="muted">Before using this with real participants, confirm your lab or university requirements for consent language and ethics review.</p>
    </div>
    <label class="field" data-required-id="consent">
      <span><input id="consentCheck" type="checkbox" ${state.consent ? "checked" : ""}> I consent to participate in this pilot study.</span>
    </label>
    <div class="button-row">
      <button class="primary" id="nextBtn">Begin</button>
    </div>
  `;
  document.getElementById("nextBtn").addEventListener("click", () => {
    const checked = document.getElementById("consentCheck").checked;
    if (!checked) {
      showErrors([{ id: "consent", message: "Consent is required to continue." }]);
      return;
    }
    state.consent = true;
    logEvent("consent_complete", {});
    nextStep();
  });
}

function renderBackground() {
  const fields = config.background_questions.map((question) => renderQuestion(question, state.background)).join("");
  app.innerHTML = `
    <h2>Background</h2>
    <p class="muted">These questions help interpret whether travel experience or transit confidence changes the effect of planning nudges.</p>
    <div class="form-grid">${fields}</div>
    <div class="button-row">
      <button class="secondary" id="backBtn">Back</button>
      <button class="primary" id="nextBtn">Continue</button>
    </div>
  `;
  bindBack();
  document.getElementById("nextBtn").addEventListener("click", async () => {
    const errors = collectQuestions(config.background_questions, state.background);
    if (errors.length) {
      showErrors(errors);
      return;
    }
    const button = document.getElementById("nextBtn");
    button.disabled = true;
    button.textContent = "Assigning...";
    await assignCondition();
    logEvent("background_complete", {});
    nextStep();
  });
}

function renderTask(taskIndex) {
  const task = getAssignedTasks()[taskIndex];
  const activeNudges = getActiveNudges(task);
  const saved = state.tasks[task.id] || {};
  const nudgeHtml = activeNudges.length
    ? `<aside class="nudge-box"><h3>Planning notes</h3><ul>${activeNudges.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></aside>`
    : `<aside class="nudge-box"><h3>Planning information</h3><p>This version provides the baseline destination description only.</p></aside>`;

  app.innerHTML = `
    <h2>${escapeHtml(task.poi_name)}</h2>
    <p>${escapeHtml(task.prompt)}</p>
    <div class="two-column">
      <article class="destination">
        <h3>${escapeHtml(task.baseline.title)}</h3>
        <ul>${task.baseline.body.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </article>
      ${nudgeHtml}
    </div>

    <div class="choice-list" role="radiogroup" aria-label="Decision" data-required-id="decision">
      <h3>Your decision</h3>
      ${task.decision_options.map((option) => `
        <label>
          <input type="radio" name="decision" value="${escapeAttr(option)}" ${saved.decision === option ? "checked" : ""}>
          <span>${escapeHtml(option)}</span>
        </label>
      `).join("")}
    </div>

    <div class="choice-list" role="radiogroup" aria-label="Accuracy check" data-required-id="accuracy">
      <h3>${escapeHtml(task.accuracy_question.label)}</h3>
      ${task.accuracy_question.options.map((option) => `
        <label>
          <input type="radio" name="accuracy" value="${escapeAttr(option)}" ${saved.accuracy_answer === option ? "checked" : ""}>
          <span>${escapeHtml(option)}</span>
        </label>
      `).join("")}
    </div>

    <label class="field full" data-required-id="decision_rationale">
      <span>Briefly explain your decision</span>
      <textarea id="decisionRationale">${escapeHtml(saved.decision_rationale || "")}</textarea>
    </label>

    <div class="button-row">
      <button class="secondary" id="backBtn">Back</button>
      <button class="primary" id="nextBtn">Continue</button>
    </div>
  `;

  bindBack();
  document.getElementById("nextBtn").addEventListener("click", () => {
    const decision = getCheckedValue("decision");
    const accuracy = getCheckedValue("accuracy");
    const rationale = document.getElementById("decisionRationale").value.trim();
    const errors = [];
    if (!decision) errors.push({ id: "decision", message: "Choose a planning decision." });
    if (!accuracy) errors.push({ id: "accuracy", message: "Choose an answer for the planning issue check." });
    if (!rationale) errors.push({ id: "decision_rationale", message: "Add a brief explanation of your decision." });
    if (errors.length) {
      showErrors(errors);
      return;
    }

    state.tasks[task.id] = {
      task_id: task.id,
      poi_name: task.poi_name,
      city: task.city,
      condition: state.assigned_condition,
      decision,
      decision_rationale: rationale,
      accuracy_answer: accuracy,
      accuracy_correct: accuracy === task.accuracy_question.correct,
      time_on_task_ms: Date.now() - stepStartedAt
    };
    logEvent("task_complete", { task_id: task.id });
    nextStep();
  });
}

function renderSurvey(taskIndex) {
  const task = getAssignedTasks()[taskIndex];
  const saved = state.surveys[task.id] || {};
  const items = [];
  config.constructs.forEach((construct) => {
    construct.items.forEach((label, index) => {
      items.push({
        id: `${construct.id}_${index + 1}`,
        construct: construct.id,
        label
      });
    });
  });

  app.innerHTML = `
    <h2>Post-task Questions</h2>
    <p class="muted">Answer based on the ${escapeHtml(task.poi_name)} planning task you just completed.</p>
    <div class="likert-stack">
      ${items.map((item) => renderLikertItem(item, saved[item.id])).join("")}
    </div>
    <div class="button-row">
      <button class="secondary" id="backBtn">Back</button>
      <button class="primary" id="nextBtn">Continue</button>
    </div>
  `;

  bindBack();
  document.getElementById("nextBtn").addEventListener("click", () => {
    const responses = {};
    const errors = [];
    items.forEach((item) => {
      const value = getCheckedValue(item.id);
      if (!value) errors.push({ id: item.id, message: `Answer: ${item.label}` });
      responses[item.id] = value ? Number(value) : "";
    });
    if (errors.length) {
      showErrors(errors);
      return;
    }
    state.surveys[task.id] = {
      task_id: task.id,
      condition: state.assigned_condition,
      ...responses,
      survey_time_ms: Date.now() - stepStartedAt
    };
    logEvent("survey_complete", { task_id: task.id });
    nextStep();
  });
}

function renderFinalQuestions() {
  const fields = config.final_questions.map((question) => renderQuestion(question, state.final)).join("");
  app.innerHTML = `
    <h2>Final Questions</h2>
    <p class="muted">These open-ended answers are useful for improving the nudge wording before a larger study.</p>
    <div class="form-grid">${fields}</div>
    <div class="button-row">
      <button class="secondary" id="backBtn">Back</button>
      <button class="primary" id="nextBtn">Finish Study</button>
    </div>
  `;
  bindBack();
  document.getElementById("nextBtn").addEventListener("click", async () => {
    const errors = collectQuestions(config.final_questions, state.final);
    if (errors.length) {
      showErrors(errors);
      return;
    }
    const button = document.getElementById("nextBtn");
    button.disabled = true;
    button.textContent = "Saving...";
    state.completed_at = new Date().toISOString();
    logEvent("study_complete", {});
    persistCompletedSession();
    await submitCurrentSession();
    nextStep();
  });
}

function renderExport() {
  const sessions = loadCompletedSessions();
  const remote = state.remote_submission || {};
  const remoteStatus = getRemoteStatusText(remote);
  const remoteClass = remote.status === "submitted" ? "success" : "muted";
  app.innerHTML = `
    <h2>Study Complete</h2>
    <p class="success">Response saved in this browser.</p>
    <p>Download the pilot data before clearing browser storage. JSON preserves the full event log; CSV is flattened for spreadsheet review and SEM preparation.</p>
    <table class="status-table">
      <tr><th>Session ID</th><td>${escapeHtml(state.session_id)}</td></tr>
      <tr><th>Condition</th><td>${escapeHtml(getCondition().label)}</td></tr>
      <tr><th>Database status</th><td class="${remoteClass}">${escapeHtml(remoteStatus)}</td></tr>
      <tr><th>Completed sessions in browser</th><td>${sessions.length}</td></tr>
    </table>
    <div class="button-row">
      <button class="secondary" id="retryBtn">Retry Database Save</button>
      <button class="secondary" id="jsonBtn">Download JSON</button>
      <button class="secondary" id="csvBtn">Download CSV</button>
      <button class="danger" id="resetBtn">Start New Participant</button>
    </div>
  `;

  document.getElementById("retryBtn").addEventListener("click", async () => {
    const retryButton = document.getElementById("retryBtn");
    retryButton.disabled = true;
    retryButton.textContent = "Retrying...";
    remoteApiAvailable = await checkRemoteApi();
    await submitCurrentSession({ force: true });
    renderExport();
  });
  document.getElementById("jsonBtn").addEventListener("click", () => {
    downloadFile("fukui_nudge_pilot_sessions.json", JSON.stringify(sessions, null, 2), "application/json");
  });
  document.getElementById("csvBtn").addEventListener("click", () => {
    downloadFile("fukui_nudge_pilot_sessions.csv", sessionsToCsv(sessions), "text/csv");
  });
  document.getElementById("resetBtn").addEventListener("click", () => {
    localStorage.removeItem(CURRENT_KEY);
    state = createState();
    stepIndex = 0;
    render();
  });
}

async function checkRemoteApi() {
  if (!window.location.protocol.startsWith("http")) return false;
  try {
    const response = await fetch(API_HEALTH_ENDPOINT, {
      method: "GET",
      headers: { "Accept": "application/json" },
      cache: "no-store"
    });
    if (!response.ok) return false;
    const result = await response.json();
    return result.status === "ok" && result.storage_configured === true;
  } catch (_error) {
    return false;
  }
}

async function submitCurrentSession(options = {}) {
  if (!state.completed_at) return;
  const remote = state.remote_submission || {};
  if (remote.status === "submitted" && !options.force) return;

  if (!remoteApiAvailable) {
    state.remote_submission = {
      status: "local_only",
      submitted_at: "",
      response_id: "",
      message: "No configured Vercel API was detected. Local export remains available."
    };
    persistCompletedSession();
    return;
  }

  state.remote_submission = {
    status: "pending",
    submitted_at: "",
    response_id: "",
    message: "Submitting response to database."
  };
  persistCompletedSession();

  try {
    const response = await fetch(API_SUBMIT_ENDPOINT, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ session: state })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok !== true) {
      throw new Error(result.error || `Database save failed with HTTP ${response.status}`);
    }
    state.remote_submission = {
      status: "submitted",
      submitted_at: new Date().toISOString(),
      response_id: result.response_id || "",
      message: "Saved to Supabase."
    };
  } catch (error) {
    state.remote_submission = {
      status: "failed",
      submitted_at: "",
      response_id: "",
      message: error instanceof Error ? error.message : "Database save failed."
    };
  }
  persistCompletedSession();
}

function getRemoteStatusText(remote) {
  if (!remote || !remote.status || remote.status === "not_started") {
    return "Not submitted yet.";
  }
  if (remote.status === "submitted") {
    return remote.response_id
      ? `Saved to Supabase (${remote.response_id}).`
      : "Saved to Supabase.";
  }
  if (remote.status === "local_only") {
    return remote.message || "Local-only mode. No database API detected.";
  }
  if (remote.status === "pending") {
    return "Submitting to database.";
  }
  if (remote.status === "failed") {
    return `Database save failed: ${remote.message || "unknown error"}`;
  }
  return remote.message || remote.status;
}

function renderQuestion(question, source) {
  const value = source[question.id] || "";
  if (question.type === "textarea") {
    return `
      <label class="field full" data-required-id="${escapeAttr(question.id)}">
        <span>${escapeHtml(question.label)}</span>
        <textarea data-question-id="${escapeAttr(question.id)}">${escapeHtml(value)}</textarea>
      </label>
    `;
  }
  if (question.type === "likert") {
    return `
      <fieldset class="field" data-required-id="${escapeAttr(question.id)}">
        <legend>${escapeHtml(question.label)}</legend>
        <div class="likert-options">
          ${[1, 2, 3, 4, 5, 6, 7].map((score) => `
            <label>
              <input type="radio" name="${escapeAttr(question.id)}" value="${score}" ${Number(value) === score ? "checked" : ""}>
              ${score}
            </label>
          `).join("")}
        </div>
        <div class="scale-anchors">
          <span>${escapeHtml(question.anchors[0])}</span>
          <span>${escapeHtml(question.anchors[1])}</span>
        </div>
      </fieldset>
    `;
  }
  return `
    <label class="field" data-required-id="${escapeAttr(question.id)}">
      <span>${escapeHtml(question.label)}</span>
      <select data-question-id="${escapeAttr(question.id)}">
        <option value="">Select</option>
        ${question.options.map((option) => `<option value="${escapeAttr(option)}" ${value === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}
      </select>
    </label>
  `;
}

function renderLikertItem(item, value) {
  return `
    <fieldset class="likert-row" data-required-id="${escapeAttr(item.id)}">
      <legend>${escapeHtml(item.label)}</legend>
      <div class="likert-options">
        ${[1, 2, 3, 4, 5, 6, 7].map((score) => `
          <label>
            <input type="radio" name="${escapeAttr(item.id)}" value="${score}" ${Number(value) === score ? "checked" : ""}>
            ${score}
          </label>
        `).join("")}
      </div>
      <div class="scale-anchors">
        <span>Strongly disagree</span>
        <span>Strongly agree</span>
      </div>
    </fieldset>
  `;
}

function collectQuestions(questions, target) {
  const errors = [];
  questions.forEach((question) => {
    let value = "";
    if (question.type === "likert") {
      value = getCheckedValue(question.id);
      target[question.id] = value ? Number(value) : "";
    } else {
      const element = document.querySelector(`[data-question-id="${CSS.escape(question.id)}"]`);
      value = element ? element.value.trim() : "";
      target[question.id] = value;
    }
    if (!value) errors.push({ id: question.id, message: `Complete: ${question.label}` });
  });
  return errors;
}

function getActiveNudges(task) {
  if (state.assigned_condition === "control") return [];
  if (state.assigned_condition === "combined") {
    return [
      ...(task.nudges.transport_access || []),
      ...(task.nudges.opening_hours_availability || []),
      ...(task.nudges.itinerary_fit_time_cost || [])
    ];
  }
  return task.nudges[state.assigned_condition] || [];
}

function getCondition() {
  return config.conditions.find((condition) => condition.id === state.assigned_condition);
}

function getCheckedValue(name) {
  const checked = document.querySelector(`input[name="${CSS.escape(name)}"]:checked`);
  return checked ? checked.value : "";
}

function bindBack() {
  const backButton = document.getElementById("backBtn");
  if (!backButton) return;
  backButton.addEventListener("click", () => {
    stepIndex = Math.max(0, stepIndex - 1);
    render({ resetScroll: true });
  });
}

function nextStep() {
  stepIndex = Math.min(steps.length - 1, stepIndex + 1);
  render({ resetScroll: true });
}

function showErrors(errors) {
  clearValidationState();
  const normalized = errors.map((error) => {
    if (typeof error === "string") return { id: "", message: error };
    return error;
  });
  const existing = app.querySelector(".error-list");
  if (existing) existing.remove();
  const summary = document.createElement("div");
  summary.className = "error-list";
  summary.setAttribute("role", "alert");
  const heading = document.createElement("p");
  heading.textContent = "Please answer the highlighted question before continuing.";
  summary.appendChild(heading);
  const list = document.createElement("ul");
  normalized.slice(0, 5).forEach((error) => {
    const item = document.createElement("li");
    item.textContent = error.message;
    list.appendChild(item);
  });
  if (normalized.length > 5) {
    const item = document.createElement("li");
    item.textContent = `Complete ${normalized.length - 5} more highlighted item${normalized.length - 5 === 1 ? "" : "s"}.`;
    list.appendChild(item);
  }
  summary.appendChild(list);
  const buttonRow = app.querySelector(".button-row");
  app.insertBefore(summary, buttonRow || null);

  normalized.forEach((error) => markInvalidQuestion(error.id));
  scrollToFirstInvalid();
}

function clearValidationState() {
  app.querySelectorAll(".is-invalid").forEach((element) => {
    element.classList.remove("is-invalid");
    element.removeAttribute("aria-invalid");
  });
}

function bindValidationClearers() {
  app.oninput = clearInvalidForEvent;
  app.onchange = clearInvalidForEvent;
}

function clearInvalidForEvent(event) {
  const wrapper = event.target.closest("[data-required-id]");
  if (!wrapper) return;
  wrapper.classList.remove("is-invalid");
  wrapper.removeAttribute("aria-invalid");
  const errorList = app.querySelector(".error-list");
  if (errorList && !app.querySelector(".is-invalid")) errorList.remove();
}

function markInvalidQuestion(id) {
  if (!id) return;
  const wrapper = app.querySelector(`[data-required-id="${CSS.escape(id)}"]`);
  if (!wrapper) return;
  wrapper.classList.add("is-invalid");
  wrapper.setAttribute("aria-invalid", "true");
}

function scrollToFirstInvalid() {
  const firstInvalid = app.querySelector(".is-invalid");
  if (!firstInvalid) return;
  firstInvalid.scrollIntoView({ block: "center", behavior: "smooth" });
  const focusTarget = firstInvalid.querySelector("input, select, textarea, button");
  if (focusTarget) focusTarget.focus({ preventScroll: true });
}

function resetPageScroll() {
  requestAnimationFrame(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    app.focus({ preventScroll: true });
  });
}

function logEvent(type, detail) {
  state.events.push({
    type,
    detail,
    timestamp: new Date().toISOString(),
    step: steps[stepIndex],
    elapsed_ms: Date.now() - stepStartedAt
  });
  saveCurrentState();
}

function saveCurrentState() {
  localStorage.setItem(CURRENT_KEY, JSON.stringify(state));
}

function loadCurrentState() {
  const raw = localStorage.getItem(CURRENT_KEY);
  return raw ? JSON.parse(raw) : null;
}

function loadCompletedSessions() {
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

function persistCompletedSession() {
  const sessions = loadCompletedSessions();
  const next = sessions.filter((session) => session.session_id !== state.session_id);
  next.push(state);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  saveCurrentState();
}

function sessionsToCsv(sessions) {
  const rows = sessions.map(flattenSession);
  const headers = Array.from(rows.reduce((set, row) => {
    Object.keys(row).forEach((key) => set.add(key));
    return set;
  }, new Set()));
  return [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header] ?? "")).join(","))
  ].join("\n");
}

function flattenSession(session) {
  const row = {
    study_id: session.study_id,
    version: session.version,
    session_id: session.session_id,
    assigned_condition: session.assigned_condition,
    assignment_method: session.assignment_method || "",
    assignment_stratum: session.assignment_stratum || "",
    assigned_task_ids: (session.assigned_task_ids || []).join("|"),
    task_order: (session.task_order || []).join("|"),
    started_at: session.started_at,
    completed_at: session.completed_at,
    remote_submission_status: session.remote_submission?.status || "",
    remote_submission_response_id: session.remote_submission?.response_id || ""
  };
  Object.entries(session.background || {}).forEach(([key, value]) => {
    row[`background_${key}`] = value;
  });
  Object.entries(session.tasks || {}).forEach(([taskId, values]) => {
    Object.entries(values).forEach(([key, value]) => {
      row[`task_${taskId}_${key}`] = value;
    });
  });
  Object.entries(session.surveys || {}).forEach(([taskId, values]) => {
    Object.entries(values).forEach(([key, value]) => {
      row[`survey_${taskId}_${key}`] = value;
    });
  });
  Object.entries(session.final || {}).forEach(([key, value]) => {
    row[`final_${key}`] = value;
  });
  row.event_count = (session.events || []).length;
  return row;
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const text = String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}
