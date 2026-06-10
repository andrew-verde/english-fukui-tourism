const MAX_BODY_BYTES = 250_000;
const TABLE_NAME = process.env.SUPABASE_TABLE || "nudge_pilot_responses";

module.exports = async function handler(request, response) {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");

  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    response.status(405).json({ ok: false, error: "Method not allowed" });
    return;
  }

  if (!process.env.SUPABASE_URL || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    response.status(503).json({
      ok: false,
      error: "Supabase environment variables are not configured"
    });
    return;
  }

  if (!isAllowedOrigin(request)) {
    response.status(403).json({
      ok: false,
      error: "Origin is not allowed"
    });
    return;
  }

  const contentLength = Number(request.headers["content-length"] || 0);
  if (contentLength > MAX_BODY_BYTES) {
    response.status(413).json({ ok: false, error: "Request body is too large" });
    return;
  }

  try {
    const body = await readJsonBody(request);
    const session = body.session;
    const validationErrors = validateSession(session);
    if (validationErrors.length) {
      response.status(400).json({
        ok: false,
        error: "Invalid study response",
        details: validationErrors
      });
      return;
    }

    const record = buildSupabaseRecord(session, request);
    const result = await upsertResponse(record);
    response.status(200).json({
      ok: true,
      response_id: result.id || record.session_id,
      session_id: record.session_id
    });
  } catch (error) {
    response.status(500).json({
      ok: false,
      error: error instanceof Error ? error.message : "Unexpected server error"
    });
  }
};

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let raw = "";
    request.on("data", (chunk) => {
      raw += chunk;
      if (Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) {
        reject(new Error("Request body is too large"));
        request.destroy();
      }
    });
    request.on("end", () => {
      try {
        resolve(JSON.parse(raw || "{}"));
      } catch (_error) {
        reject(new Error("Request body is not valid JSON"));
      }
    });
    request.on("error", reject);
  });
}

function validateSession(session) {
  const errors = [];
  if (!session || typeof session !== "object") {
    return ["Missing session object"];
  }
  requiredString(session.study_id, "study_id", errors);
  requiredString(session.version, "version", errors);
  requiredString(session.session_id, "session_id", errors);
  requiredString(session.assigned_condition, "assigned_condition", errors);
  requiredString(session.started_at, "started_at", errors);
  requiredString(session.completed_at, "completed_at", errors);

  if (session.consent !== true) {
    errors.push("consent must be true");
  }
  if (!session.background || typeof session.background !== "object") {
    errors.push("background must be an object");
  }
  if (!session.tasks || typeof session.tasks !== "object" || Object.keys(session.tasks).length === 0) {
    errors.push("tasks must contain at least one task response");
  }
  if (!session.surveys || typeof session.surveys !== "object" || Object.keys(session.surveys).length === 0) {
    errors.push("surveys must contain at least one survey response");
  }
  if (!session.final || typeof session.final !== "object") {
    errors.push("final must be an object");
  }
  if (!Array.isArray(session.events)) {
    errors.push("events must be an array");
  }
  if (JSON.stringify(session).length > MAX_BODY_BYTES) {
    errors.push("session payload is too large");
  }
  return errors;
}

function requiredString(value, field, errors) {
  if (typeof value !== "string" || value.trim() === "") {
    errors.push(`${field} is required`);
  }
}

function buildSupabaseRecord(session, request) {
  const flattened = flattenSession(session);
  return {
    study_id: session.study_id,
    study_version: session.version,
    session_id: session.session_id,
    assigned_condition: session.assigned_condition,
    started_at: session.started_at,
    completed_at: session.completed_at,
    consent: session.consent === true,
    background: session.background || {},
    tasks: session.tasks || {},
    surveys: session.surveys || {},
    final_responses: session.final || {},
    events: session.events || [],
    flattened,
    user_agent: String(request.headers["user-agent"] || "").slice(0, 500),
    app_source: "vercel",
    received_at: new Date().toISOString()
  };
}

function isAllowedOrigin(request) {
  const origin = request.headers.origin;
  if (!origin) return true;

  const host = request.headers.host;
  if (host) {
    try {
      if (new URL(origin).host === host) return true;
    } catch (_error) {
      return false;
    }
  }

  const allowed = (process.env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return allowed.includes(origin);
}

async function upsertResponse(record) {
  const baseUrl = process.env.SUPABASE_URL.replace(/\/+$/, "");
  const url = `${baseUrl}/rest/v1/${TABLE_NAME}?on_conflict=session_id`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "apikey": process.env.SUPABASE_SERVICE_ROLE_KEY,
      "Authorization": `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
      "Prefer": "resolution=merge-duplicates,return=representation"
    },
    body: JSON.stringify(record)
  });

  const text = await response.text();
  let parsed;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch (_error) {
    parsed = text;
  }

  if (!response.ok) {
    const detail = typeof parsed === "object" && parsed ? (parsed.message || parsed.details || parsed.hint) : parsed;
    throw new Error(detail || `Supabase request failed with HTTP ${response.status}`);
  }

  if (Array.isArray(parsed) && parsed.length > 0) {
    return parsed[0];
  }
  return record;
}

function flattenSession(session) {
  const row = {
    study_id: session.study_id,
    version: session.version,
    session_id: session.session_id,
    assigned_condition: session.assigned_condition,
    started_at: session.started_at,
    completed_at: session.completed_at
  };
  Object.entries(session.background || {}).forEach(([key, value]) => {
    row[`background_${key}`] = value;
  });
  Object.entries(session.tasks || {}).forEach(([taskId, values]) => {
    Object.entries(values || {}).forEach(([key, value]) => {
      row[`task_${taskId}_${key}`] = value;
    });
  });
  Object.entries(session.surveys || {}).forEach(([taskId, values]) => {
    Object.entries(values || {}).forEach(([key, value]) => {
      row[`survey_${taskId}_${key}`] = value;
    });
  });
  Object.entries(session.final || {}).forEach(([key, value]) => {
    row[`final_${key}`] = value;
  });
  row.event_count = (session.events || []).length;
  return row;
}
